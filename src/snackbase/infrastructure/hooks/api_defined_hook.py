"""API-Defined Event Hook Dispatcher for F8.1.

Registers a single callback per supported event type in the HookRegistry.
At runtime each callback queries the database for matching enabled event-type
hooks, evaluates optional conditions, executes actions, and logs the result.

This mirrors the webhook_hook.py pattern: background tasks for non-blocking
dispatch, session_factory for DB access, no per-hook registration overhead.

Supported events:
    records.create  → ON_RECORD_AFTER_CREATE
    records.update  → ON_RECORD_AFTER_UPDATE
    records.delete  → ON_RECORD_AFTER_DELETE
    auth.login      → ON_AUTH_AFTER_LOGIN
    auth.register   → ON_AUTH_AFTER_REGISTER
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Optional, Set

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)

# Keep references to prevent background tasks from being GC'd early
_background_tasks: Set[asyncio.Task] = set()

# Map internal hook event names → public API event string
_EVENT_MAP: dict[str, str] = {
    HookEvent.ON_RECORD_AFTER_CREATE: "records.create",
    HookEvent.ON_RECORD_AFTER_UPDATE: "records.update",
    HookEvent.ON_RECORD_AFTER_DELETE: "records.delete",
    HookEvent.ON_AUTH_AFTER_LOGIN: "auth.login",
    HookEvent.ON_AUTH_AFTER_REGISTER: "auth.register",
}

# Events where record + collection context is available
_RECORD_EVENTS = {
    HookEvent.ON_RECORD_AFTER_CREATE,
    HookEvent.ON_RECORD_AFTER_UPDATE,
    HookEvent.ON_RECORD_AFTER_DELETE,
}


def register_api_defined_hooks(registry: HookRegistry, session_factory: Any) -> list[str]:
    """Register event dispatchers for all supported API-defined hook events.

    A single dispatcher per event type is registered (not per hook). At runtime
    each dispatcher queries the DB for matching hooks, so hot-reload of
    hook create/update/delete is automatic.

    Args:
        registry: The HookRegistry to register with.
        session_factory: Async session factory (db_manager.session).

    Returns:
        List of registered hook IDs.
    """
    hook_ids = []

    for internal_event, api_event in _EVENT_MAP.items():
        async def _dispatcher(
            _event: str,
            data: Optional[dict[str, Any]],
            context: Optional[HookContext],
            _api_event: str = api_event,
            _internal_event: str = internal_event,
            _session_factory: Any = session_factory,
        ) -> Optional[dict[str, Any]]:
            # Dispatch as a background task so it never blocks the caller
            task = asyncio.create_task(
                _dispatch_api_hooks(
                    internal_event=_internal_event,
                    api_event=_api_event,
                    data=data,
                    context=context,
                    session_factory=_session_factory,
                )
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
            return data

        hook_ids.append(
            registry.register(
                event=internal_event,
                callback=_dispatcher,
                priority=300,  # after audit (100) and webhook (200) hooks
                is_builtin=False,
            )
        )

    logger.info("API-defined event hook dispatchers registered", count=len(hook_ids))
    return hook_ids


async def _dispatch_api_hooks(
    internal_event: str,
    api_event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
    session_factory: Any,
) -> None:
    """Query matching hooks and execute them.

    Args:
        internal_event: HookEvent constant (e.g. "on_record_after_create").
        api_event: Public event string (e.g. "records.create").
        data: Hook data containing record, collection, old_values.
        context: Hook context with account_id, user.
        session_factory: Async session factory.
    """
    if context is None or not context.account_id:
        return

    account_id = context.account_id
    record: dict[str, Any] = {}
    collection: str | None = None

    if internal_event in _RECORD_EVENTS and data:
        record = data.get("record") or {}
        collection = data.get("collection")
        if not record and not collection:
            return
    elif data:
        # For auth events, build a synthetic record from whatever is available
        record = {k: v for k, v in data.items() if k not in ("session",)}

    from snackbase.infrastructure.persistence.repositories.hook_repository import HookRepository
    from snackbase.infrastructure.persistence.repositories.hook_execution_repository import (
        HookExecutionRepository,
    )
    from snackbase.infrastructure.persistence.models.hook_execution import HookExecutionModel
    from snackbase.infrastructure.hooks.action_executor import execute_actions

    try:
        async with session_factory() as session:
            hook_repo = HookRepository(session)
            hooks = await hook_repo.list_event_hooks_for_account(
                account_id=account_id,
                event_name=api_event,
                collection=collection,
            )

        for hook in hooks:
            await _run_hook(
                hook=hook,
                trigger_type="event",
                record=record,
                context=context,
                session_factory=session_factory,
                execute_actions=execute_actions,
            )

    except Exception as exc:
        logger.error(
            "API-defined hook dispatcher encountered an error",
            api_event=api_event,
            account_id=account_id,
            error=str(exc),
        )


async def _run_hook(
    hook: Any,
    trigger_type: str,
    record: dict[str, Any],
    context: Optional[HookContext],
    session_factory: Any,
    execute_actions: Any,
) -> None:
    """Evaluate condition, execute actions, and log the result for one hook."""
    from snackbase.infrastructure.persistence.models.hook_execution import HookExecutionModel
    from snackbase.infrastructure.persistence.repositories.hook_execution_repository import (
        HookExecutionRepository,
    )

    # Evaluate optional condition
    if hook.condition:
        if not _evaluate_condition(hook.condition, record):
            logger.debug(
                "Hook condition did not match — skipping",
                hook_id=hook.id,
                condition=hook.condition,
            )
            return

    start_ms = time.monotonic()
    actions_executed = 0
    error_message: str | None = None
    status = "success"

    try:
        actions_executed, error_message = await execute_actions(
            actions=hook.actions or [],
            record=record,
            context=context,
            session_factory=session_factory,
            depth=0,
        )
        if error_message:
            status = "partial" if actions_executed > 0 else "failed"
    except Exception as exc:
        error_message = str(exc)
        status = "failed"
        logger.error("Hook execution raised unexpected error", hook_id=hook.id, error=str(exc))

    duration_ms = int((time.monotonic() - start_ms) * 1000)

    # Build a safe snapshot of the execution context (avoid serialization issues)
    exec_context: dict[str, Any] = {
        "event": trigger_type,
        "account_id": context.account_id if context else None,
        "record_id": record.get("id"),
        "collection": record.get("collection"),
    }

    try:
        from snackbase.infrastructure.persistence.models.hook import HookModel

        async with session_factory() as session:
            exec_repo = HookExecutionRepository(session)
            execution = HookExecutionModel(
                hook_id=hook.id,
                trigger_type=trigger_type,
                status=status,
                actions_executed=actions_executed,
                error_message=error_message,
                duration_ms=duration_ms,
                execution_context=exec_context,
                executed_at=datetime.now(UTC),
            )
            await exec_repo.create(execution)

            # Update hook's last_run_at
            hook_obj = await session.get(HookModel, hook.id)
            if hook_obj is not None:
                hook_obj.last_run_at = datetime.now(UTC)

            await session.commit()
    except Exception as exc:
        logger.error("Failed to log hook execution", hook_id=hook.id, error=str(exc))

    logger.info(
        "API-defined hook executed",
        hook_id=hook.id,
        hook_name=hook.name,
        trigger_type=trigger_type,
        status=status,
        actions_executed=actions_executed,
        duration_ms=duration_ms,
    )


def _evaluate_condition(condition: str, record: dict[str, Any]) -> bool:
    """Evaluate a simple rule expression against the record dict.

    Delegates to the same filter evaluator used by webhook filters.
    Returns True if condition is met (or if evaluation fails, logs and returns True
    to avoid silently skipping hooks due to bad condition syntax).
    """
    try:
        from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
        return _evaluate_filter(condition, record)
    except Exception as exc:
        logger.warning(
            "Hook condition evaluation failed — executing hook anyway",
            condition=condition,
            error=str(exc),
        )
        return True


async def execute_hook_manually(
    hook: Any,
    context: Optional[HookContext],
    session_factory: Any,
) -> tuple[int, str | None]:
    """Execute a hook's actions directly (for manual triggers).

    Returns (actions_executed, error_message).
    """
    from snackbase.infrastructure.hooks.action_executor import execute_actions

    actions_executed, error_message = await execute_actions(
        actions=hook.actions or [],
        record={},
        context=context,
        session_factory=session_factory,
        depth=0,
    )

    status = "success"
    if error_message:
        status = "partial" if actions_executed > 0 else "failed"

    try:
        from snackbase.infrastructure.persistence.models.hook_execution import HookExecutionModel
        from snackbase.infrastructure.persistence.repositories.hook_execution_repository import (
            HookExecutionRepository,
        )

        from snackbase.infrastructure.persistence.models.hook import HookModel

        async with session_factory() as session:
            exec_repo = HookExecutionRepository(session)
            execution = HookExecutionModel(
                hook_id=hook.id,
                trigger_type="manual",
                status=status,
                actions_executed=actions_executed,
                error_message=error_message,
                execution_context={"trigger": "manual"},
                executed_at=datetime.now(UTC),
            )
            await exec_repo.create(execution)

            hook_obj = await session.get(HookModel, hook.id)
            if hook_obj is not None:
                hook_obj.last_run_at = datetime.now(UTC)

            await session.commit()
    except Exception as exc:
        logger.error("Failed to log manual hook execution", hook_id=hook.id, error=str(exc))

    return actions_executed, error_message
