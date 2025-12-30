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

    # Only process model operation events
    if not event.startswith("on_model_after_"):
        return data

    # Extract model from data
    model = data.get("model")
    if model is None:
        logger.warning("Audit capture hook: no model in data", hook_event=event)
        return data

    # Extract user context
    user = context.user
    if user is None:
        logger.debug("Audit capture hook: no user context, skipping audit")
        return data

    # Get account_id from model or context
    account_id = getattr(model, "account_id", None) or context.account_id
    if not account_id:
        logger.warning("Audit capture hook: no account_id found")
        return data

    # Import here to avoid circular dependency
    from snackbase.domain.services import AuditLogService
    from snackbase.infrastructure.persistence.database import get_db_session

    # Get database session from context
    # Note: We need to get a new session for audit logging
    # to avoid interfering with the main transaction
    try:
        # Use the same session as the main operation
        # The audit repository will handle the transaction
        session = data.get("session")
        if session is None:
            logger.warning("Audit capture hook: no session in data")
            return data

        audit_service = AuditLogService(session)

        # Extract user groups
        user_groups = getattr(user, "groups", [])
        if isinstance(user_groups, list) and user_groups:
            # If groups are objects, extract names
            if hasattr(user_groups[0], "name"):
                user_groups = [g.name for g in user_groups]

        # Capture audit based on event type
        if event == HookEvent.ON_MODEL_AFTER_CREATE:
            await audit_service.capture_create(
                model=model,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                user_groups=user_groups,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )
        elif event == HookEvent.ON_MODEL_AFTER_UPDATE:
            old_values = data.get("old_values", {})
            await audit_service.capture_update(
                model=model,
                old_values=old_values,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                user_groups=user_groups,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )
        elif event == HookEvent.ON_MODEL_AFTER_DELETE:
            await audit_service.capture_delete(
                model=model,
                user_id=str(user.id),
                user_email=user.email,
                user_name=context.user_name or getattr(user, "name", user.email),
                account_id=str(account_id),
                user_groups=user_groups,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
            )

    except Exception as e:
        # Log error but don't fail the main operation
        logger.error(
            "Audit capture hook failed",
            hook_event=event,
            error=str(e),
            exc_info=True,
        )

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
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_MODEL_AFTER_CREATE,
            callback=audit_capture_hook,
            priority=100,
            is_builtin=True,
        )
    )
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_MODEL_AFTER_UPDATE,
            callback=audit_capture_hook,
            priority=100,
            is_builtin=True,
        )
    )
    hook_ids.append(
        registry.register(
            event=HookEvent.ON_MODEL_AFTER_DELETE,
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
