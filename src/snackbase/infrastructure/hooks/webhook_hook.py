"""Webhook delivery hook for SnackBase.

Registers hooks that fire outbound webhooks when record events occur.
Webhook delivery is asynchronous and does NOT block the record operation.
"""

from typing import Any, Optional

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)

# Map hook event names to webhook event names
_EVENT_MAP = {
    HookEvent.ON_RECORD_AFTER_CREATE: "records.create",
    HookEvent.ON_RECORD_AFTER_UPDATE: "records.update",
    HookEvent.ON_RECORD_AFTER_DELETE: "records.delete",
}

# Map webhook event names to the "events" field values in WebhookModel
_WEBHOOK_EVENT_NAMES = {
    "records.create": "create",
    "records.update": "update",
    "records.delete": "delete",
}


def register_webhook_hooks(registry: HookRegistry, session_factory: Any) -> list[str]:
    """Register webhook delivery hooks.

    These hooks fire after record operations and dispatch outbound HTTP
    webhooks that match the event, collection, and optional filter.

    Args:
        registry: The HookRegistry to register hooks with.
        session_factory: Async session factory (db_manager.session).

    Returns:
        List of registered hook IDs.
    """
    hook_ids = []

    for event in [
        HookEvent.ON_RECORD_AFTER_CREATE,
        HookEvent.ON_RECORD_AFTER_UPDATE,
        HookEvent.ON_RECORD_AFTER_DELETE,
    ]:
        webhook_event = _EVENT_MAP[event]

        async def _webhook_hook(
            _event: str,
            data: Optional[dict[str, Any]],
            context: Optional[HookContext],
            # Capture loop variables via default args
            _webhook_event: str = webhook_event,
            _session_factory: Any = session_factory,
        ) -> Optional[dict[str, Any]]:
            return await _dispatch_webhooks(
                event=_event,
                webhook_event=_webhook_event,
                data=data,
                context=context,
                session_factory=_session_factory,
            )

        hook_ids.append(
            registry.register(
                event=event,
                callback=_webhook_hook,
                priority=200,  # Run after audit_capture_hook (priority 100)
                is_builtin=False,
            )
        )

    logger.info("Webhook delivery hooks registered", hook_count=len(hook_ids))
    return hook_ids


async def _dispatch_webhooks(
    event: str,
    webhook_event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
    session_factory: Any,
) -> Optional[dict[str, Any]]:
    """Internal: look up matching webhooks and fire them.

    Args:
        event: Hook event name (e.g., "on_record_after_create").
        webhook_event: Webhook event name (e.g., "records.create").
        data: Hook data containing "record", "collection", "old_values", "session".
        context: Hook context with account_id.
        session_factory: Async session factory.

    Returns:
        Unmodified data (webhook dispatch doesn't alter the record).
    """
    if data is None or context is None:
        return data

    record = data.get("record")
    collection = data.get("collection")
    if not record or not collection:
        return data

    account_id = context.account_id
    if not account_id:
        return data

    previous = data.get("old_values") if webhook_event == "records.update" else (
        record if webhook_event == "records.delete" else None
    )
    # For delete, record IS the previous; current record is None
    current_record = None if webhook_event == "records.delete" else record

    from snackbase.core.config import get_settings
    from snackbase.infrastructure.persistence.repositories.webhook_repository import (
        WebhookRepository,
    )
    from snackbase.infrastructure.webhooks.webhook_service import (
        _evaluate_filter,
        dispatch_webhook,
    )

    settings = get_settings()
    timeout = getattr(settings, "webhook_timeout_seconds", 30)
    event_key = _WEBHOOK_EVENT_NAMES.get(webhook_event, "")

    try:
        async with session_factory() as session:
            webhook_repo = WebhookRepository(session)
            webhooks = await webhook_repo.list_enabled_by_collection(account_id, collection)

        for webhook in webhooks:
            # Check if this webhook listens to this event type
            if event_key not in (webhook.events or []):
                continue

            # Evaluate optional filter expression
            if webhook.filter:
                record_for_filter = current_record or record
                if not _evaluate_filter(webhook.filter, record_for_filter):
                    logger.debug(
                        "Webhook filter did not match — skipping",
                        webhook_id=webhook.id,
                        collection=collection,
                    )
                    continue

            # Fire delivery as background task
            try:
                await dispatch_webhook(
                    webhook=webhook,
                    event_type=webhook_event,
                    record=current_record or {},
                    previous=previous,
                    session_factory=session_factory,
                    timeout_seconds=timeout,
                )
            except Exception as exc:
                logger.error(
                    "Failed to dispatch webhook",
                    webhook_id=webhook.id,
                    error=str(exc),
                )

    except Exception as exc:
        logger.error(
            "Webhook hook encountered an error",
            event=event,
            collection=collection,
            error=str(exc),
        )

    return data
