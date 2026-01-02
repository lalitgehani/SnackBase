"""Built-in hooks for SnackBase.

These hooks provide core system functionality and CANNOT be disabled.
They are registered as built-in hooks with negative priority to ensure
they run before or after user hooks as appropriate.

Built-in hooks in Phase 1:
- timestamp_hook: Sets created_at/updated_at timestamps
- account_isolation_hook: Ensures account_id is set on records
"""

from datetime import datetime, timezone
from typing import Any, Optional

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)


async def timestamp_hook(
    event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
) -> Optional[dict[str, Any]]:
    """Built-in hook to set created_at and updated_at timestamps.

    This hook automatically sets:
    - created_at: On record creation
    - updated_at: On record creation and update

    Args:
        event: The hook event name.
        data: The record data.
        context: The hook context.

    Returns:
        Modified data with timestamps set.
    """
    if data is None:
        return data

    now = datetime.now(timezone.utc).isoformat()

    if event == HookEvent.ON_RECORD_BEFORE_CREATE:
        # Set both created_at and updated_at on create
        data["created_at"] = now
        data["updated_at"] = now
        logger.debug("Timestamp hook: Set created_at and updated_at", timestamp=now)

    elif event == HookEvent.ON_RECORD_BEFORE_UPDATE:
        # Set only updated_at on update
        data["updated_at"] = now
        logger.debug("Timestamp hook: Set updated_at", timestamp=now)

    return data


async def account_isolation_hook(
    event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
) -> Optional[dict[str, Any]]:
    """Built-in hook to ensure account_id isolation.

    This hook enforces multi-tenancy by:
    - Setting account_id from context on record create
    - Validating account_id matches on record updates

    Args:
        event: The hook event name.
        data: The record data.
        context: The hook context.

    Returns:
        Modified data with account_id set.

    Raises:
        AbortHookException: If account_id doesn't match (update).
    """
    if data is None or context is None:
        return data

    if context.account_id:
        if event == HookEvent.ON_RECORD_BEFORE_CREATE:
            # Set account_id from context
            data["account_id"] = context.account_id
            logger.debug(
                "Account isolation hook: Set account_id",
                account_id=context.account_id,
            )

    return data


async def created_by_hook(
    event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
) -> Optional[dict[str, Any]]:
    """Built-in hook to set created_by and updated_by fields.

    Args:
        event: The hook event name.
        data: The record data.
        context: The hook context.

    Returns:
        Modified data with user tracking fields set.
    """
    if data is None or context is None:
        return data

    user_id = context.user.id if context.user else None

    if event == HookEvent.ON_RECORD_BEFORE_CREATE:
        if user_id:
            data["created_by"] = user_id
            data["updated_by"] = user_id
            logger.debug("Created by hook: Set created_by and updated_by", user_id=user_id)

    elif event == HookEvent.ON_RECORD_BEFORE_UPDATE:
        if user_id:
            data["updated_by"] = user_id
            logger.debug("Created by hook: Set updated_by", user_id=user_id)

    return data


async def audit_capture_hook(
    event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext],
) -> Optional[dict[str, Any]]:
    """Built-in hook to capture audit log entries for model operations.

    This hook automatically captures audit trails for CREATE, UPDATE, DELETE
    operations on SQLAlchemy models with column-level granularity.

    Args:
        event: The hook event name.
        data: The record data (contains 'model' and optionally 'old_values').
        context: The hook context with user and request information.

    Returns:
        Unmodified data (audit capture doesn't modify the operation).
    """
    if data is None or context is None:
        return data

    # Only process model or record operation events
    if not (event.startswith("on_model_after_") or event.startswith("on_record_after_")):
        return data

    # Extract model or record from data
    model = data.get("model")
    record_data = data.get("record")
    collection_name = data.get("collection")

    if model is None and record_data is None:
        logger.warning("Audit capture hook: no model or record in data", hook_event=event)
        return data

    # If it's a record event, wrap the record data in a snapshot
    if record_data is not None and collection_name is not None:
        from snackbase.infrastructure.persistence.record_snapshot import RecordSnapshot
        from snackbase.infrastructure.persistence.table_builder import TableBuilder
        
        table_name = TableBuilder.generate_table_name(collection_name)
        model = RecordSnapshot(table_name, record_data)
    
    if model is None:
        logger.warning("Audit capture hook: failed to resolve model/record", hook_event=event)
        return data

    # Extract user context
    user = context.user
    if user is None:
        logger.debug("Audit capture hook: no user context, skipping audit")
        return data

    # Get account_id from model or context
    # Use robust extraction to handle AccountModel which doesn't have account_id field
    account_id = getattr(model, "account_id", None) or context.account_id
    
    # Special case: If audit is for AccountModel creation, use its own ID if not found
    if not account_id and hasattr(model, "__tablename__") and model.__tablename__ == "accounts":
         account_id = getattr(model, "id", None)

    if not account_id:
        logger.warning("Audit capture hook: no account_id found")
        return data

    # Import here to avoid circular dependency
    from snackbase.domain.services import AuditLogService
    from snackbase.infrastructure.persistence.database import get_db_manager

    # Get database session
    # 1. Try to get logic-session passed in data (from manual triggers)
    session = data.get("session")
    
    # 2. If None (from global listener), create a new dedicated session
    should_close_session = False
    if session is None:
        db = get_db_manager()
        session_factory = db.session_factory
        session = session_factory()
        should_close_session = True

    try:
        audit_service = AuditLogService(session)

        # Capture audit based on event type
        # Note: user_groups no longer needed for capture - masking happens on read
        if event in (HookEvent.ON_MODEL_AFTER_CREATE, HookEvent.ON_RECORD_AFTER_CREATE):
            await audit_service.capture_create(
                model=model,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )
        elif event in (HookEvent.ON_MODEL_AFTER_UPDATE, HookEvent.ON_RECORD_AFTER_UPDATE):
            old_values = data.get("old_values", {})
            await audit_service.capture_update(
                model=model,
                old_values=old_values,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )
        elif event in (HookEvent.ON_MODEL_AFTER_DELETE, HookEvent.ON_RECORD_AFTER_DELETE):
            await audit_service.capture_delete(
                model=model,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )

        if should_close_session:
            await session.commit()

    except Exception as e:
        if should_close_session and session:
            await session.rollback()

        # Log error but don't fail the main operation
        logger.error(
            "Audit capture hook failed",
            hook_event=event,
            error=str(e),
            exc_info=True,
        )
    finally:
        if should_close_session and session:
            await session.close()

    return data


def register_builtin_hooks(registry: HookRegistry) -> list[str]:
    """Register all built-in hooks.

    Built-in hooks are registered with:
    - is_builtin=True (cannot be unregistered)
    - Negative priority (run before/after user hooks appropriately)

    Args:
        registry: The HookRegistry to register hooks with.

    Returns:
        List of registered hook IDs.
    """
    hook_ids = []

    # Timestamp hook - runs early on before_create and before_update
    # Use priority -100 to run before user hooks
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            callback=timestamp_hook,
            priority=-100,
            is_builtin=True,
        )
    )
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            callback=timestamp_hook,
            priority=-100,
            is_builtin=True,
        )
    )

    # Account isolation hook - runs very early
    # Use priority -200 to run before timestamp hook
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            callback=account_isolation_hook,
            priority=-200,
            is_builtin=True,
        )
    )

    # Created by hook - runs after account isolation
    # Use priority -150 to run between account isolation and timestamp
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            callback=created_by_hook,
            priority=-150,
            is_builtin=True,
        )
    )
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            callback=created_by_hook,
            priority=-150,
            is_builtin=True,
        )
    )

    # Audit capture hooks - run after all other hooks (positive priority)
    # Use priority 100 to run after user hooks
    
    # Model events (ORM)
    # Model events (ORM)
    # NOTE: Model audit logging is now handled synchronously in event_listeners.py
    # to prevent database lock issues with SQLite. We NO LONGER register the async hook
    # for model events.

    # Record events (Dynamic Collections)
    for event in [
        HookEvent.ON_RECORD_AFTER_CREATE,
        HookEvent.ON_RECORD_AFTER_UPDATE,
        HookEvent.ON_RECORD_AFTER_DELETE,
    ]:
        hook_ids.append(
            registry.register(
                event=event,
                callback=audit_capture_hook,
                priority=100,
                is_builtin=True,
            )
        )

    logger.info(
        "Built-in hooks registered",
        hook_count=len(hook_ids),
        hook_ids=hook_ids,
    )

    return hook_ids


# Dictionary of built-in hook functions for reference
BUILTIN_HOOKS = {
    "timestamp_hook": timestamp_hook,
    "account_isolation_hook": account_isolation_hook,
    "created_by_hook": created_by_hook,
    "audit_capture_hook": audit_capture_hook,
}
