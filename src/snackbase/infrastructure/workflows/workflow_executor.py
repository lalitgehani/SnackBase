"""Workflow execution engine (F8.3).

Provides ``run_instance()`` — the core loop that executes a workflow instance
step by step — and ``resume_instance()`` called by the job worker after a
``wait_delay`` step elapses.

Step type dispatch:
    action      → reuses execute_actions() from action_executor (F8.1)
    condition   → evaluates a rule expression, branches to on_true/on_false
    wait_delay  → enqueues a workflow_resume job, transitions instance to waiting
    wait_condition → not yet implemented (marks step skipped with a warning)
    wait_event  → not yet implemented (marks step skipped with a warning)
    loop        → iterates over resolved items, calls inner step for each
    parallel    → asyncio.gather over branch chains

Template variables available inside step configs:
    {{trigger.<field>}}              — from instance.context["trigger"]
    {{steps.<step_name>.output.<field>}} — output from a previous step
    {{now}}                          — current UTC ISO timestamp
    {{auth.user_id}}, {{auth.email}} — from hook context (when available)
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from snackbase.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d)$")

_DURATION_UNITS: dict[str, int] = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}


def _parse_duration(value: str) -> timedelta:
    """Parse a simple duration string like '5m', '2h', '1d' into a timedelta."""
    m = _DURATION_RE.match(value.strip().lower())
    if not m:
        raise ValueError(
            f"Invalid duration {value!r}. Expected format: <number><unit> "
            "where unit is s/m/h/d (e.g. '5m', '2h', '1d')"
        )
    amount = int(m.group(1))
    unit = m.group(2)
    return timedelta(seconds=amount * _DURATION_UNITS[unit])


# ---------------------------------------------------------------------------
# Template resolution (extends action_executor._resolve_value)
# ---------------------------------------------------------------------------

_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")


def _resolve_template_workflow(
    value: str,
    context: dict[str, Any],
) -> str:
    """Replace {{...}} placeholders using the workflow instance context."""
    trigger: dict[str, Any] = context.get("trigger") or {}
    steps_ctx: dict[str, Any] = context.get("steps") or {}
    now_str = datetime.now(UTC).isoformat()

    def _replace(match: re.Match) -> str:
        var = match.group(1).strip()

        if var == "now":
            return now_str

        if var.startswith("trigger."):
            field = var[len("trigger."):]
            val = trigger.get(field)
            return str(val) if val is not None else ""

        if var.startswith("steps."):
            # steps.<step_name>.output.<field>
            parts = var.split(".", 3)
            if len(parts) >= 4 and parts[2] == "output":
                step_name = parts[1]
                field = parts[3]
                step_data = steps_ctx.get(step_name) or {}
                val = (step_data.get("output") or {}).get(field)
                return str(val) if val is not None else ""

        # Unknown variable — leave as-is
        return match.group(0)

    return _TEMPLATE_RE.sub(_replace, value)


def _resolve_value_workflow(value: Any, context: dict[str, Any]) -> Any:
    """Recursively resolve template variables using workflow context."""
    if isinstance(value, str):
        return _resolve_template_workflow(value, context)
    if isinstance(value, dict):
        return {k: _resolve_value_workflow(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value_workflow(item, context) for item in value]
    return value


# ---------------------------------------------------------------------------
# Step execution helpers
# ---------------------------------------------------------------------------


async def _execute_action_step(
    step: dict[str, Any],
    instance_context: dict[str, Any],
    account_id: str,
    session_factory: Any,
) -> dict[str, Any]:
    """Execute an ``action`` step using the F8.1 action executor."""
    from snackbase.infrastructure.hooks.action_executor import execute_actions

    action_type = step.get("action_type", "")
    config: dict[str, Any] = step.get("config") or {}

    # Resolve templates in the config
    resolved_config = _resolve_value_workflow(config, instance_context)

    action_def = {"type": action_type, **resolved_config}

    # Build a minimal HookContext so the action executor can access account_id
    from snackbase.domain.entities.hook_context import HookContext

    ctx = HookContext(app=None, account_id=account_id)

    executed, error = await execute_actions(
        actions=[action_def],
        record=instance_context.get("trigger") or {},
        context=ctx,
        session_factory=session_factory,
        depth=0,
    )

    if error:
        raise RuntimeError(error)

    return {"executed": executed}


def _evaluate_expression(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a rule expression against the workflow context trigger data."""
    try:
        from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter

        trigger = context.get("trigger") or {}
        return _evaluate_filter(expression, trigger)
    except Exception as exc:
        logger.warning(
            "Workflow condition evaluation failed — treating as True",
            expression=expression,
            error=str(exc),
        )
        return True


async def _execute_condition_step(
    step: dict[str, Any],
    instance_context: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    """Evaluate a condition step. Returns (next_step_name, output)."""
    expression = step.get("expression", "")
    result = _evaluate_expression(expression, instance_context)
    next_step = step.get("on_true") if result else step.get("on_false")
    return next_step, {"result": result, "branch": "true" if result else "false"}


async def _execute_wait_delay_step(
    step: dict[str, Any],
    instance_id: str,
    next_step: str | None,
    account_id: str,
    session_factory: Any,
) -> None:
    """Enqueue a resume job for after the delay period. Instance becomes 'waiting'."""
    duration_str = step.get("duration", "5m")
    delay = _parse_duration(duration_str)
    run_at = datetime.now(UTC) + delay

    from snackbase.infrastructure.services.job_service import JobService

    svc = JobService(session_factory)
    job_id = await svc.enqueue(
        handler="workflow_resume",
        payload={"instance_id": instance_id, "next_step": next_step},
        queue="workflows",
        run_at=run_at,
        max_retries=3,
        account_id=account_id,
    )
    return job_id


async def _execute_loop_step(
    step: dict[str, Any],
    instance_context: dict[str, Any],
    account_id: str,
    workflow_steps: dict[str, dict[str, Any]],
    instance_id: str,
    session_factory: Any,
) -> dict[str, Any]:
    """Execute the target step for each item in a resolved list."""
    items_template = step.get("items", "")
    inner_step_name = step.get("step", "")

    # Resolve the items expression
    resolved = _resolve_value_workflow(items_template, instance_context)
    if isinstance(resolved, str):
        # If it didn't resolve to a list, try evaluating it as a context key
        items: list[Any] = []
    elif isinstance(resolved, list):
        items = resolved
    else:
        items = [resolved]

    inner_step = workflow_steps.get(inner_step_name)
    if inner_step is None:
        raise ValueError(f"Loop references unknown step '{inner_step_name}'")

    outputs = []
    for idx, item in enumerate(items):
        # Inject current item into context temporarily
        loop_context = dict(instance_context)
        loop_context["loop_item"] = item
        loop_context["loop_index"] = idx

        output = await _execute_single_step_inline(
            inner_step, loop_context, account_id, workflow_steps, instance_id, session_factory
        )
        outputs.append(output)

    return {"items_count": len(items), "outputs": outputs}


async def _execute_parallel_step(
    step: dict[str, Any],
    instance_context: dict[str, Any],
    account_id: str,
    workflow_steps: dict[str, dict[str, Any]],
    instance_id: str,
    session_factory: Any,
) -> dict[str, Any]:
    """Execute branch chains concurrently via asyncio.gather."""
    branches: list[list[str]] = step.get("branches") or []

    async def _run_branch(step_names: list[str]) -> list[Any]:
        branch_outputs = []
        for sname in step_names:
            s = workflow_steps.get(sname)
            if s is None:
                raise ValueError(f"Parallel branch references unknown step '{sname}'")
            out = await _execute_single_step_inline(
                s, instance_context, account_id, workflow_steps, instance_id, session_factory
            )
            branch_outputs.append(out)
        return branch_outputs

    results = await asyncio.gather(*[_run_branch(b) for b in branches], return_exceptions=True)

    errors = [str(r) for r in results if isinstance(r, Exception)]
    if errors:
        raise RuntimeError(f"Parallel branch failures: {'; '.join(errors)}")

    return {"branch_results": [r for r in results if not isinstance(r, Exception)]}


async def _execute_single_step_inline(
    step: dict[str, Any],
    instance_context: dict[str, Any],
    account_id: str,
    workflow_steps: dict[str, dict[str, Any]],
    instance_id: str,
    session_factory: Any,
) -> dict[str, Any]:
    """Execute one step inline (used by loop/parallel sub-execution)."""
    step_type = step.get("type", "")

    if step_type == "action":
        return await _execute_action_step(step, instance_context, account_id, session_factory)
    elif step_type == "condition":
        _, output = await _execute_condition_step(step, instance_context)
        return output
    else:
        logger.warning("Unsupported step type in inline context", step_type=step_type)
        return {}


# ---------------------------------------------------------------------------
# Main execution loop
# ---------------------------------------------------------------------------


async def run_instance(
    instance_id: str,
    session_factory: Any,
    *,
    start_step: str | None = None,
) -> None:
    """Execute a workflow instance from the current (or given) step.

    Loads the instance and its parent workflow from the DB, then runs steps
    sequentially until the workflow completes, fails, or pauses (wait_delay).

    This function is safe to call from a background task or job handler.

    Args:
        instance_id: ID of the WorkflowInstanceModel to execute.
        session_factory: Async session factory (db_manager.session).
        start_step: Override the step to start from (used by resume_instance).
    """
    from snackbase.infrastructure.persistence.models.workflow import WorkflowModel
    from snackbase.infrastructure.persistence.models.workflow_instance import WorkflowInstanceModel
    from snackbase.infrastructure.persistence.models.workflow_step_log import WorkflowStepLogModel
    from snackbase.infrastructure.persistence.repositories.workflow_instance_repository import (
        WorkflowInstanceRepository,
    )
    from snackbase.infrastructure.persistence.repositories.workflow_step_log_repository import (
        WorkflowStepLogRepository,
    )

    # Load instance
    async with session_factory() as session:
        inst = await session.get(WorkflowInstanceModel, instance_id)
        if inst is None:
            logger.error("workflow_run_instance: instance not found", instance_id=instance_id)
            return
        if inst.status in ("completed", "cancelled"):
            logger.debug(
                "workflow_run_instance: instance already in terminal state",
                instance_id=instance_id,
                status=inst.status,
            )
            return

        wf = await session.get(WorkflowModel, inst.workflow_id)
        if wf is None:
            logger.error(
                "workflow_run_instance: workflow not found", workflow_id=inst.workflow_id
            )
            inst.status = "failed"
            inst.error_message = "Parent workflow not found"
            inst.completed_at = datetime.now(UTC)
            await session.commit()
            return

        # Snapshot mutable state before session closes
        steps_list: list[dict[str, Any]] = list(wf.steps or [])
        account_id: str = inst.account_id
        workflow_id: str = wf.id
        instance_context: dict[str, Any] = dict(inst.context or {})
        current_step_name: str | None = start_step or inst.current_step

        # Transition to running
        inst.status = "running"
        await session.commit()

    # Build step index
    workflow_steps: dict[str, dict[str, Any]] = {s["name"]: s for s in steps_list if "name" in s}

    # Determine starting point
    if current_step_name and current_step_name in workflow_steps:
        step_order = [s["name"] for s in steps_list]
        start_idx = step_order.index(current_step_name)
        remaining_steps = steps_list[start_idx:]
    else:
        # Begin at the first step
        remaining_steps = steps_list

    if not remaining_steps:
        async with session_factory() as session:
            inst = await session.get(WorkflowInstanceModel, instance_id)
            if inst:
                inst.status = "completed"
                inst.completed_at = datetime.now(UTC)
                await session.commit()
        logger.info("Workflow instance completed (no steps)", instance_id=instance_id)
        return

    # Execute steps one by one
    # We re-open a session per-step to persist progress incrementally
    step_iter = iter(remaining_steps)
    explicit_next: str | None = None  # set by condition/wait steps

    while True:
        if explicit_next is not None:
            step = workflow_steps.get(explicit_next)
            explicit_next = None
            if step is None:
                break  # explicit_next pointed at nothing → workflow ends
        else:
            try:
                step = next(step_iter)
            except StopIteration:
                break

        step_name = step.get("name", "?")
        step_type = step.get("type", "")
        step_next = step.get("next")

        logger.debug(
            "Executing workflow step",
            instance_id=instance_id,
            step=step_name,
            step_type=step_type,
        )

        started_at = datetime.now(UTC)
        step_output: dict[str, Any] = {}
        step_status = "success"
        step_error: str | None = None
        paused = False

        try:
            if step_type == "action":
                step_output = await _execute_action_step(
                    step, instance_context, account_id, session_factory
                )

            elif step_type == "condition":
                explicit_next, step_output = await _execute_condition_step(
                    step, instance_context
                )
                # condition overrides the sequential step_next
                step_next = None

            elif step_type == "wait_delay":
                actual_next = step.get("next")
                job_id = await _execute_wait_delay_step(
                    step, instance_id, actual_next, account_id, session_factory
                )
                step_output = {"resume_job_id": job_id, "duration": step.get("duration")}
                paused = True

            elif step_type == "loop":
                step_output = await _execute_loop_step(
                    step, instance_context, account_id,
                    workflow_steps, instance_id, session_factory
                )

            elif step_type == "parallel":
                step_output = await _execute_parallel_step(
                    step, instance_context, account_id,
                    workflow_steps, instance_id, session_factory
                )

            elif step_type in ("wait_condition", "wait_event"):
                # Not yet implemented: log a warning and skip
                logger.warning(
                    "Step type not yet implemented — skipping",
                    step_type=step_type,
                    step_name=step_name,
                    instance_id=instance_id,
                )
                step_status = "skipped"
                step_output = {"skipped_reason": f"{step_type} not yet implemented"}

            else:
                logger.warning(
                    "Unknown step type — skipping",
                    step_type=step_type,
                    step_name=step_name,
                )
                step_status = "skipped"
                step_output = {"skipped_reason": f"Unknown step type: {step_type!r}"}

        except Exception as exc:
            step_status = "failed"
            step_error = str(exc)
            logger.error(
                "Workflow step failed",
                instance_id=instance_id,
                step=step_name,
                error=str(exc),
            )

        completed_at = datetime.now(UTC)

        # Persist step log + update instance context
        async with session_factory() as session:
            step_log = WorkflowStepLogModel(
                instance_id=instance_id,
                workflow_id=workflow_id,
                account_id=account_id,
                step_name=step_name,
                step_type=step_type,
                status=step_status,
                input={k: v for k, v in step.items() if k not in ("type", "name")},
                output=step_output,
                error_message=step_error,
                started_at=started_at,
                completed_at=completed_at,
            )
            session.add(step_log)

            inst = await session.get(WorkflowInstanceModel, instance_id)
            if inst is None:
                await session.commit()
                return

            inst.current_step = step_name

            # Update accumulated context with this step's output
            ctx = dict(inst.context or {})
            steps_section = dict(ctx.get("steps") or {})
            steps_section[step_name] = {"output": step_output, "status": step_status}
            ctx["steps"] = steps_section
            inst.context = ctx
            instance_context = ctx  # keep in-memory copy current

            if step_status == "failed":
                inst.status = "failed"
                inst.error_message = step_error
                inst.completed_at = datetime.now(UTC)
                await session.commit()
                logger.info(
                    "Workflow instance failed",
                    instance_id=instance_id,
                    step=step_name,
                    error=step_error,
                )
                return

            if paused:
                inst.status = "waiting"
                inst.resume_job_id = step_output.get("resume_job_id")
                await session.commit()
                logger.info(
                    "Workflow instance paused (wait_delay)",
                    instance_id=instance_id,
                    step=step_name,
                )
                return

            await session.commit()

        if step_next and step_type != "condition":
            # Jump to the named next step (skips sequential iteration)
            explicit_next = step_next
            step_iter = iter([])  # exhaust the sequential iterator

    # All steps executed successfully
    async with session_factory() as session:
        inst = await session.get(WorkflowInstanceModel, instance_id)
        if inst:
            inst.status = "completed"
            inst.completed_at = datetime.now(UTC)
            await session.commit()

    logger.info("Workflow instance completed", instance_id=instance_id)


async def resume_instance(
    instance_id: str,
    next_step: str | None,
    session_factory: Any,
) -> None:
    """Resume a waiting (or failed) workflow instance.

    Called by the ``workflow_resume`` job handler after a ``wait_delay`` elapses,
    or by the API ``POST /workflow-instances/{id}/resume`` endpoint.

    Args:
        instance_id: ID of the instance to resume.
        next_step: Step name to resume from (None = continue sequentially).
        session_factory: Async session factory.
    """
    from snackbase.infrastructure.persistence.models.workflow_instance import WorkflowInstanceModel

    async with session_factory() as session:
        inst = await session.get(WorkflowInstanceModel, instance_id)
        if inst is None:
            logger.error("resume_instance: instance not found", instance_id=instance_id)
            return
        if inst.status == "cancelled":
            logger.info("resume_instance: instance was cancelled, skipping", instance_id=instance_id)
            return
        if inst.status == "completed":
            logger.debug("resume_instance: instance already completed", instance_id=instance_id)
            return

        inst.status = "running"
        inst.resume_job_id = None
        await session.commit()

    await run_instance(instance_id, session_factory, start_step=next_step)
