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

# Track registered listeners for cleanup (Issue #7)
_registered_listeners: list[tuple[Any, str, Any]] = []


class ModelSnapshot:
    """A detached snapshot of a model's state for async processing.
    
    This class mimics enough of the SQLAlchemy model interface to be used
    by the AuditLogService without triggering lazy loads or requiring an active session.
    """
    def __init__(self, model: Any):
        self.__tablename__ = getattr(model, "__tablename__", None)
        self.__is_snapshot__ = True
        
        # Capture class name for logging/debugging
        self.__class_name__ = model.__class__.__name__
        
        # Inspect model to get primary key and columns
        from sqlalchemy import inspect
        
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

        # Capture history for updates if applicable
        self.__history__ = {}
        for attr in instance_state.attrs:
            # Only track simple columns, skip relationships to avoid lazy loads
            if hasattr(attr, "history") and attr.key in [c.name for c in mapper.columns]:
                try:
                    # Accessing history on loaded attributes is generally safe
                    # but we only do it if the attribute is in the instance dict
                    if attr.key in instance_dict and attr.history.has_changes():
                        self.__history__[attr.key] = {
                            "added": attr.history.added,
                            "deleted": attr.history.deleted,
                        }
                except Exception:
                    # Fail gracefully if history access fails
                    pass


def register_sqlalchemy_listeners(engine: Any, hook_registry: HookRegistry) -> None:
    """Register global SQLAlchemy event listeners.

    Args:
        engine: The SQLAlchemy engine (or class) to bind listeners to.
                Can be the Engine instance or the Mapper class.
        hook_registry: The hook registry to trigger events on.
    """
    from sqlalchemy.orm import Mapper
    
    # Define listeners
    listeners = [
        (Mapper, "after_insert", _make_listener(hook_registry, "insert")),
        (Mapper, "after_update", _make_listener(hook_registry, "update")),
        (Mapper, "after_delete", _make_listener(hook_registry, "delete")),
    ]

    # Register and track for cleanup
    for target, name, callback in listeners:
        event.listen(target, name, callback)
        _registered_listeners.append((target, name, callback))
    
    logger.info("Registered global SQLAlchemy audit listeners")


def unregister_sqlalchemy_listeners() -> None:
    """Unregister all registered SQLAlchemy event listeners.

    This is primarily used for test isolation to prevent listeners from
    accumulating or affecting unrelated tests.
    """
    for target, name, callback in _registered_listeners:
        try:
            event.remove(target, name, callback)
        except Exception as e:
            logger.warning(f"Failed to remove SQLAlchemy listener: {e}")

    _registered_listeners.clear()
    logger.info("Unregistered all global SQLAlchemy audit listeners")


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
            # Background task or system op without context -> skip audit
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
            
        # 3. Safe Data Extraction & Snapshot
        # Using the ModelSnapshot ensures we don't trigger lazy loads in async driver
        snapshot = ModelSnapshot(target)

        # 4. Synchronous Audit Logging using existing connection
        try:
            from sqlalchemy.exc import MissingGreenlet
            
            from snackbase.domain.services.audit_log_service import AuditLogService
            from snackbase.infrastructure.persistence.repositories.sync_audit_log_repository import SyncAuditLogRepository
            
            # Helper to check for sensitive data masking
            def mask_sensitive_helper(col_name, val):
                # We use a temporary instance of AuditLogService (without session for masking only)
                # or just use the static/class method if it were one. 
                # For now, we can just instantiate it or use the logic directly.
                # Since mask_sensitive_only doesn't use self.session, we can call it.
                service = AuditLogService(None)
                return service.mask_sensitive_only(col_name, val)

            # Get record ID from snapshot
            record_id = (
                str(getattr(snapshot, snapshot.primary_key_name))
                if snapshot.primary_key_name
                else None
            )
                
            if not record_id:
                logger.warning(f"Cannot audit {op_type.upper()} for {table_name}: no record ID found")
            else:
                # Determine account_id
                account_id = getattr(snapshot, "account_id", None) or context.account_id
                # Special case: If audit is for AccountModel creation, use its own ID if not found
                if not account_id and table_name == "accounts":
                     account_id = getattr(snapshot, "id", None)

                if account_id:
                    sync_repo = SyncAuditLogRepository(connection)
                    audit_entries = []
                    
                    if op_type == "insert":
                        # Audit all columns from snapshot
                        for column in mapper.columns:
                            new_val = getattr(snapshot, column.name, None)
                            masked_val = mask_sensitive_helper(column.name, new_val)
                            
                            audit_entries.append({
                                "account_id": str(account_id),
                                "operation": "CREATE",
                                "table_name": table_name,
                                "record_id": record_id,
                                "column_name": column.name,
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
                        # Audit changed columns using snapshot history
                        for col_name, history in snapshot.__history__.items():
                            new_val = history["added"][0] if history["added"] else None
                            old_val = history["deleted"][0] if history["deleted"] else None
                                
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
                        # Audit all columns as deleted from snapshot
                        for column in mapper.columns:
                            old_val = getattr(snapshot, column.name, None)
                            masked_val = mask_sensitive_helper(column.name, old_val)
                            
                            audit_entries.append({
                                "account_id": str(account_id),
                                "operation": "DELETE",
                                "table_name": table_name,
                                "record_id": record_id,
                                "column_name": column.name,
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
            # This should now be rare given the ModelSnapshot refactor
            logger.warning(
                f"Audit logging skipped: MissingGreenlet during {op_type.upper()} {table_name}. "
                "This usually happens when accessing unloaded attributes in a sync listener "
                "with an async driver. Ensure audit-critical columns are loaded.",
                error=str(e),
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

        # 5. Trigger Async Hooks (User Hooks)
        # We still want to allow users to register hooks, so we keep the async trigger
        if op_type == "insert":
            event_name = HookEvent.ON_MODEL_AFTER_CREATE
        elif op_type == "update":
            event_name = HookEvent.ON_MODEL_AFTER_UPDATE
        else:
            event_name = HookEvent.ON_MODEL_AFTER_DELETE

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def trigger_async():
            try:
                data = {
                    "model": snapshot,
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
