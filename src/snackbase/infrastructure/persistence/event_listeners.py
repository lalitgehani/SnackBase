"""SQLAlchemy event listeners for audit logging.

This module registers global event listeners for SQLAlchemy models to automatically
trigger audit hooks when records are created, updated, or deleted.
It bridges the gap between the ORM and the HookRegistry using the global context.
"""

import asyncio
from typing import Any, Set

from sqlalchemy import event
from sqlalchemy.orm import Session

from snackbase.core.context import get_current_context
from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.audit_helper import AuditHelper
from snackbase.infrastructure.persistence.models import AccountModel

logger = get_logger(__name__)

# Track background tasks to prevent them from being garbage collected
# and to allow for proper cleanup if needed.
_background_tasks: Set[asyncio.Task] = set()


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
        from sqlalchemy.exc import InvalidRequestError
        
        try:
            mapper = inspect(model.__class__)
        except Exception:
            # If inspection fails, just return empty snapshot
            self.primary_key_name = None
            return
        
        # Get primary key name
        pk_columns = [col.name for col in mapper.primary_key]
        self.primary_key_name = pk_columns[0] if pk_columns else None
        
        # Access the instance state directly to avoid triggering lazy loads
        # This is the safest way to get values in a synchronous event listener
        # when using an async driver.
        instance_state = inspect(model)
        instance_dict = instance_state.dict
        
        # Capture all column values safely
        for column in mapper.columns:
            # Check if value is in instance dict (meaning it's loaded)
            if column.name in instance_dict:
                setattr(self, column.name, instance_dict[column.name])
            else:
                # If not loaded, don't trigger lazy load, just set to None
                setattr(self, column.name, None)


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
            return

        # Special casing for AccountModel to fix the missing account_id issue
        if isinstance(target, AccountModel):
            from dataclasses import replace
            if not context.account_id:
                # If context lacks account_id, use the new account's ID
                context = replace(context, account_id=target.id)

        # 2. Determine operation and table name
        table_name = target.__tablename__
        
        # Skip excluded tables
        from snackbase.domain.services.audit_log_service import AuditLogService
        if table_name in AuditLogService.EXCLUDED_TABLES:
            return
            
        # 3. Synchronous Audit Logging using existing connection
        try:
            from snackbase.infrastructure.persistence.repositories.sync_audit_log_repository import SyncAuditLogRepository
            from snackbase.domain.services.audit_log_service import AuditLogService
            from sqlalchemy import inspect
            from sqlalchemy.exc import MissingGreenlet
            
            # Helper to check for sensitive data masking
            def mask_sensitive_helper(col_name, val):
                # We use a temporary instance of AuditLogService (without session for masking only)
                # or just use the static/class method if it were one. 
                # For now, we can just instantiate it or use the logic directly.
                # Since mask_sensitive_only doesn't use self.session, we can call it.
                service = AuditLogService(None)
                return service.mask_sensitive_only(col_name, val)

            # Get record ID
            # Copied from AuditLogService._get_record_id logic
            pk_keys = [col.name for col in mapper.primary_key]
            if pk_keys:
                pk_val = getattr(target, pk_keys[0], None)
                record_id = str(pk_val) if pk_val is not None else None
            else:
                record_id = None
                
            if not record_id:
                logger.warning(f"Cannot audit {op_type.upper()} for {table_name}: no record ID found")
            else:
                # Extract values synchronously
                instance_dict = inspect(target).dict
                columns = mapper.columns
                
                # Determine account_id
                account_id = getattr(target, "account_id", None) or context.account_id
                # Special case: If audit is for AccountModel creation, use its own ID if not found
                if not account_id and table_name == "accounts":
                     account_id = getattr(target, "id", None)

                if account_id:
                    sync_repo = SyncAuditLogRepository(connection)
                    audit_entries = []
                    
                    if op_type == "insert":
                        # Audit all columns
                        for col in columns:
                            new_val = instance_dict.get(col.name)
                            masked_val = mask_sensitive_helper(col.name, new_val)
                            
                            audit_entries.append({
                                "account_id": str(account_id),
                                "operation": "CREATE",
                                "table_name": table_name,
                                "record_id": record_id,
                                "column_name": col.name,
                                "old_value": None,
                                "new_value": str(masked_val) if masked_val is not None else None,
                                "user_id": str(context.user.id) if context.user else "system",
                                "user_email": context.user.email if context.user else "system",
                                "user_name": context.user_name or (context.user.email if context.user else "system"),
                                "ip_address": context.ip_address,
                                "user_agent": context.user_agent,
                                "request_id": context.request_id,
                            })
                            
                    elif op_type == "update":
                        # Audit changed columns
                        # Use SQLAlchemy history
                        insp = inspect(target)
                        for attr in insp.attrs:
                            if attr.history.has_changes():
                                col_name = attr.key
                                # history.added contains new values, history.deleted contains old values
                                # For update, we want single value vs single value usually
                                new_val = attr.value
                                old_val = attr.history.deleted[0] if attr.history.deleted else None
                                
                                if new_val != old_val:
                                    masked_new = mask_sensitive_helper(col_name, new_val)
                                    masked_old = mask_sensitive_helper(col_name, old_val)
                                    
                                    audit_entries.append({
                                        "account_id": str(account_id),
                                        "operation": "UPDATE",
                                        "table_name": table_name,
                                        "record_id": record_id,
                                        "column_name": col_name,
                                        "old_value": str(masked_old) if masked_old is not None else None,
                                        "new_value": str(masked_new) if masked_new is not None else None,
                                        "user_id": str(context.user.id) if context.user else "system",
                                        "user_email": context.user.email if context.user else "system",
                                        "user_name": context.user_name or (context.user.email if context.user else "system"),
                                        "ip_address": context.ip_address,
                                        "user_agent": context.user_agent,
                                        "request_id": context.request_id,
                                    })
                                    
                    elif op_type == "delete":
                        # Audit all columns as deleted
                        for col in columns:
                            try:
                                # For delete, instance_dict might be empty or partial?
                                # Usually target is fully loaded or we access attrs
                                old_val = getattr(target, col.name, None)
                            except:
                                old_val = None
                                
                            masked_val = mask_sensitive_helper(col.name, old_val)
                            
                            audit_entries.append({
                                "account_id": str(account_id),
                                "operation": "DELETE",
                                "table_name": table_name,
                                "record_id": record_id,
                                "column_name": col.name,
                                "old_value": str(masked_val) if masked_val is not None else None,
                                "new_value": None,
                                "user_id": str(context.user.id) if context.user else "system",
                                "user_email": context.user.email if context.user else "system",
                                "user_name": context.user_name or (context.user.email if context.user else "system"),
                                "ip_address": context.ip_address,
                                "user_agent": context.user_agent,
                                "request_id": context.request_id,
                            })

                    # Perform sync insert
                    if audit_entries:
                        sync_repo.create_batch(audit_entries)
                        
        except MissingGreenlet as e:
            # MissingGreenlet occurs when sync event listener tries to access
            # attributes that trigger lazy loading with async driver (aiosqlite).
            # Log warning and continue - don't fail the main operation for audit.
            logger.warning(
                f"Audit logging skipped due to async context issue for {op_type.upper()} {table_name}", 
                error=str(e)
            )
        except Exception as e:
            logger.error(
                f"Synchronous audit capture failed for {op_type.upper()} {table_name}", 
                error=str(e),
                exc_info=True
            )
            # In GxP context, we might want to RAISE here to abort transaction
            # For now, log and continue to not block the main operation
            # raise e

        # 4. Trigger Async Hooks (User Hooks)
        # We still want to allow users to register hooks, so we keep the async trigger
        if op_type == "insert":
            event_name = HookEvent.ON_MODEL_AFTER_CREATE
        elif op_type == "update":
            event_name = HookEvent.ON_MODEL_AFTER_UPDATE
        else:
            event_name = HookEvent.ON_MODEL_AFTER_DELETE

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        # Snapshot for async access
        model_snapshot = ModelSnapshot(target)
        
        # We NO LONGER pass 'session' to the hook data for Model events.
        # This prevents the built-in audit hook from trying to use it if it were still registered.
        # User hooks that need DB access should request a new session or check documentation.
        # (Usually hooks for notification/external systems don't need sync DB session)
        
        async def trigger_async():
            try:
                data = {
                    "model": model_snapshot,
                    "session": None, 
                }
                # Add old_values for update if needed (captured previously if implemented)
                # For now simplified as focus is fixing the crash.
                
                await hook_registry.trigger(event_name, data, context)
            except Exception as e:
                logger.error(
                    f"Background hook execution failed for {event_name}",
                    error=str(e),
                    exc_info=True
                )

        task = asyncio.create_task(trigger_async())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return listener
