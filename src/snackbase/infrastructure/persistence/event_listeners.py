"""SQLAlchemy event listeners for audit logging.

This module registers global event listeners for SQLAlchemy models to automatically
trigger audit hooks when records are created, updated, or deleted.
It bridges the gap between the ORM and the HookRegistry using the global context.
"""

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from snackbase.core.context import get_current_context
from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.audit_helper import AuditHelper
from snackbase.infrastructure.persistence.models import AccountModel

logger = get_logger(__name__)


class ModelSnapshot:
    """A detached snapshot of a model's state for async processing.
    
    This class mimics enough of the SQLAlchemy model interface to be used
    by the AuditLogService without triggering lazy loads or requiring an active session.
    """
    def __init__(self, model: Any):
        self.__tablename__ = model.__tablename__
        self.__is_snapshot__ = True
        
        # Capture class name for logging/debugging
        self.__class_name__ = model.__class__.__name__
        
        # Inspect model to get primary key and columns
        from sqlalchemy import inspect
        mapper = inspect(model.__class__)
        
        # Get primary key name
        pk_columns = [col.name for col in mapper.primary_key]
        self.primary_key_name = pk_columns[0] if pk_columns else None
        
        # Capture all column values
        # We use strict attribute access where possible, but safely
        for column in mapper.columns:
            val = getattr(model, column.name, None)
            setattr(self, column.name, val)


def register_sqlalchemy_listeners(engine: Any, hook_registry: HookRegistry) -> None:
    """Register global SQLAlchemy event listeners.

    Args:
        engine: The SQLAlchemy engine (or class) to bind listeners to.
                Can be the Engine instance or the Mapper class.
        hook_registry: The hook registry to trigger events on.
    """
    from sqlalchemy.orm import Mapper
    
    # We bind to Mapper to catch all model operations
    event.listen(Mapper, "after_insert", _make_listener(hook_registry, "insert"))
    event.listen(Mapper, "after_update", _make_listener(hook_registry, "update"))
    event.listen(Mapper, "after_delete", _make_listener(hook_registry, "delete"))
    
    logger.info("Registered global SQLAlchemy audit listeners")


def _make_listener(hook_registry: HookRegistry, op_type: str):
    """Factory to create a listener function for a specific operation type.
    
    Args:
        hook_registry: The registry to trigger hooks on.
        op_type: 'insert', 'update', or 'delete'.
    """
    
    def listener(mapper, connection, target):
        """The actual event listener callback."""
        # 1. Get current context
        context = get_current_context()
        if not context:
            # Background task or system op without context -> skip audit (or log warning)
            # For now silently skip to avoid noise in migrations/scripts
            return

        # 2. Get the session (needed for the hook data)
        # In newer SQLAlchemy, target might be detached or session might be on connection
        # But usually we can't easily get the AsyncSession here because these are Sync events
        # running inside the greenlet.
        # However, the hook system is Async. We cannot await here!
        
        # SOLUTION: We must schedule the async hook trigger to run after the event.
        # But since we are likely inside an async loop (FastAPI), we can't easily
        # "fire and forget" an async task from a sync context without a loop reference.
        
        # ALTERNATIVE: Use the AuditHelper logic but adapted.
        # Actually, `hook_registry.trigger` is async. We can't call it directly from here.
        
        # WORKAROUND: We can simply enqueue this to be run. 
        # OR, we assume there is a running loop and use a utility to bridge sync->async.
        
        import asyncio
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (e.g. sync script), skip
            return

        # Determine event name
        if op_type == "insert":
            event_name = HookEvent.ON_MODEL_AFTER_CREATE
        elif op_type == "update":
            event_name = HookEvent.ON_MODEL_AFTER_UPDATE
        else:
            event_name = HookEvent.ON_MODEL_AFTER_DELETE

        # Special casing for AccountModel to fix the missing account_id issue
        # If we are creating an account, the model itself is the account context
        if isinstance(target, AccountModel):
            # Create a shallow copy of context to avoid polluting the global one for this request
            # But context is mutable so we just modify it momentarily? No, better to copy.
            # Actually, `HookContext` is a dataclass.
            from dataclasses import replace
            if not context.account_id:
               # If context lacks account_id (e.g. superadmin creating account),
               # use the new account's ID as the context
               context = replace(context, account_id=target.id)

        # Capture old values for updates synchronously BEFORE async task
        old_values = {}
        if op_type == "update":
            from sqlalchemy import inspect
            insp = inspect(target)
            for attr in insp.attrs:
                if attr.history.has_changes():
                    # history.deleted contains the old value ([0])
                    if attr.history.deleted:
                        old_values[attr.key] = str(attr.history.deleted[0])

        # Verify we pass the session correctly.
        # `connection` is a Connection, not Session. 
        # The hook expects `data['session']` to be an AsyncSession for further DB ops.
        # But we don't have the high-level AsyncSession here easily. 
        # However, `audit_capture_hook` creates a NEW session using `dbsession` factory anyway?
        # Let's check `builtin_hooks.py`.
        # It tried: `session = data.get("session")`... -> `audit_service = AuditLogService(session)`
        
        # Wait, strictly speaking, triggers shouldn't do heavy DB I/O in the same transaction 
        # if likely to cause issues. But audit log NEEDS to be in same transaction for consistency?
        # No, audit log says "We need to get a new session ... to avoid interfering".
        # So passing `None` as session might force it to create one? 
        # `audit_capture_hook` line 186 checks for session.
        
        # Let's see if we can get the session from the target state or object_session(target).
        from sqlalchemy.orm import object_session
        session = object_session(target)
        
        # If this is a sync session (from the event), we can't pass it to async code 
        # that expects AsyncSession. 
        # BUT SnackBase uses AsyncSession everywhere. The `session` object here MIGHT 
        # be the `AsyncSession` proxy or the underlying `Session`.
        # If it's the sync Session inside the AsyncSession, we can't use it in async hook.
        
        # STRATEGY CHANGE: 
        # Instead of passing the session, let the hook create a new session if one isn't provided.
        # We need to modify `audit_capture_hook` to handle missing session by creating a new one scope.
        
        # Create a snapshot of the model to pass to async task
        # This prevents MissingGreenlet errors when accessing attributes later
        model_snapshot = ModelSnapshot(target)

        # Define the async trigger function
        async def trigger_async():
            data = {
                "model": model_snapshot,
                "session": None, # Signal to hook to create its own session
                "old_values": old_values
            }
            
            # If op is update/delete, we might need to handle 'old_values'.
            # Snapshotting old values happens BEFORE insert for 'update' usually.
            # But here we are in 'after_update'. The 'target' has new values.
            # 'get_history' might be needed.
            # For simplicity, `AuditHelper.capture_old_values` inspects the object.
            # If called in `after_update`, does it see old values?
            # SQLAlchemy `AttributeState` history:
            # `inspect(target).attrs.colname.history.deleted` has old values.
            
            if op_type == "update" and old_values:
                 data["old_values"] = old_values

            await hook_registry.trigger(event_name, data, context)

        # Schedule it
        # Note: 'loop.create_task' might not be safe if the loop finishes before task. 
        # But in FastAPI request cycle, this is fine.
        loop.create_task(trigger_async())

    return listener
