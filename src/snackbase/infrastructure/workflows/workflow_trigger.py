"""Workflow event-trigger dispatcher (F8.3).

Registers a single callback per supported event type in the HookRegistry.
At runtime each callback queries the DB for matching enabled event-type
workflows, creates a new WorkflowInstance, and runs it as a background task.

This mirrors the api_defined_hook.py pattern: background tasks for
non-blocking dispatch, session_factory for DB access, hot-reload automatic
because each trigger queries the DB fresh.

Supported events:
    records.create  → ON_RECORD_AFTER_CREATE
    records.update  → ON_RECORD_AFTER_UPDATE
    records.delete  → ON_RECORD_AFTER_DELETE
    auth.login      → ON_AUTH_AFTER_LOGIN
    auth.register   → ON_AUTH_AFTER_REGISTER
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Optional, Set

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)

_background_tasks: Set[asyncio.Task] = set()

_EVENT_MAP: dict[str, str] = {
    HookEvent.ON_RECORD_AFTER_CREATE: "records.create",
    HookEvent.ON_RECORD_AFTER_UPDATE: "records.update",
    HookEvent.ON_RECORD_AFTER_DELETE: "records.delete",
    HookEvent.ON_AUTH_AFTER_LOGIN: "auth.login",
    HookEvent.ON_AUTH_AFTER_REGISTER: "auth.register",
}

_RECORD_EVENTS = {
    HookEvent.ON_RECORD_AFTER_CREATE,
    HookEvent.ON_RECORD_AFTER_UPDATE,
    HookEvent.ON_RECORD_AFTER_DELETE,
}


def register_workflow_event_triggers(
    registry: HookRegistry,
    session_factory: Any,
) -> list[str]:
    """Register event dispatchers for workflow event triggers.

    A single dispatcher per event type is registered. At runtime each
    dispatcher queries the DB for matching workflows, so hot-reload of
    workflow create/update/delete is automatic.

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
            task = asyncio.create_task(
                _dispatch_workflow_triggers(
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
                priority=400,  # after API-defined hooks (300)
                is_builtin=False,
            )
        )

    logger.info("Workflow event trigger dispatchers registered", count=len(hook_ids))
    return hook_ids


async def _dispatch_workflow_triggers(
    internal_event: str,
    api_event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
    session_factory: Any,
) -> None:
    """Query matching workflows and create+run an instance for each."""
    if context is None or not context.account_id:
        return

    account_id = context.account_id
    trigger_data: dict[str, Any] = {}
    collection: str | None = None

    if internal_event in _RECORD_EVENTS and data:
        trigger_data = data.get("record") or {}
        collection = data.get("collection")
        if not trigger_data and not collection:
            return
    elif data:
        trigger_data = {k: v for k, v in data.items() if k != "session"}

    from snackbase.infrastructure.persistence.repositories.workflow_repository import (
        WorkflowRepository,
    )

    try:
        async with session_factory() as session:
            wf_repo = WorkflowRepository(session)
            workflows = await wf_repo.list_event_workflows_for_account(
                account_id=account_id,
                event_name=api_event,
                collection=collection,
            )

        for wf in workflows:
            # Evaluate optional trigger condition
            condition = (wf.trigger_config or {}).get("condition")
            if condition and not _evaluate_condition(condition, trigger_data):
                logger.debug(
                    "Workflow trigger condition did not match — skipping",
                    workflow_id=wf.id,
                )
                continue

            task = asyncio.create_task(
                _create_and_run_instance(
                    workflow_id=wf.id,
                    account_id=account_id,
                    trigger_data=trigger_data,
                    trigger_event=api_event,
                    session_factory=session_factory,
                )
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

    except Exception as exc:
        logger.error(
            "Workflow event dispatcher encountered an error",
            api_event=api_event,
            account_id=account_id,
            error=str(exc),
        )


async def _create_and_run_instance(
    workflow_id: str,
    account_id: str,
    trigger_data: dict[str, Any],
    trigger_event: str,
    session_factory: Any,
) -> None:
    """Create a WorkflowInstance and immediately start execution."""
    from snackbase.infrastructure.persistence.models.workflow_instance import WorkflowInstanceModel
    from snackbase.infrastructure.persistence.repositories.workflow_instance_repository import (
        WorkflowInstanceRepository,
    )
    from snackbase.infrastructure.workflows.workflow_executor import run_instance

    try:
        async with session_factory() as session:
            inst = WorkflowInstanceModel(
                workflow_id=workflow_id,
                account_id=account_id,
                status="pending",
                context={"trigger": {**trigger_data, "_event": trigger_event}, "steps": {}},
                started_at=datetime.now(UTC),
            )
            repo = WorkflowInstanceRepository(session)
            await repo.create(inst)
            await session.commit()
            instance_id = inst.id

        logger.info(
            "Workflow instance created for event trigger",
            workflow_id=workflow_id,
            instance_id=instance_id,
            trigger_event=trigger_event,
        )

        await run_instance(instance_id, session_factory)

    except Exception as exc:
        logger.error(
            "Failed to create/run workflow instance",
            workflow_id=workflow_id,
            error=str(exc),
        )


def _evaluate_condition(condition: str, record: dict[str, Any]) -> bool:
    try:
        from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter

        return _evaluate_filter(condition, record)
    except Exception as exc:
        logger.warning(
            "Workflow trigger condition evaluation failed — triggering anyway",
            condition=condition,
            error=str(exc),
        )
        return True
