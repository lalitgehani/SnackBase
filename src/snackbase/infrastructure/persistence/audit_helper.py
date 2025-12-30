"""Helper for triggering audit hooks from repositories.

This module provides a helper class that repositories can use to automatically
trigger audit log capture hooks for model operations.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sqlalchemy_inspect

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.domain.entities.hook_context import HookContext

logger = logging.getLogger(__name__)


class AuditHelper:
    """Helper class for triggering audit hooks from repositories.
    
    This class provides methods to trigger audit capture hooks for
    CREATE, UPDATE, DELETE operations on SQLAlchemy models.
    
    Usage:
        class MyRepository:
            def __init__(self, session: AsyncSession, hook_registry: HookRegistry):
                self.session = session
                self.audit_helper = AuditHelper(session, hook_registry)
            
            async def create(self, model: MyModel, context: HookContext) -> MyModel:
                self.session.add(model)
                await self.session.flush()
                await self.audit_helper.trigger_create(model, context)
                return model
    """
    
    def __init__(self, session: AsyncSession, hook_registry: Optional[Any] = None):
        """Initialize the audit helper.
        
        Args:
            session: SQLAlchemy async session.
            hook_registry: Optional hook registry for triggering hooks.
        """
        self.session = session
        self.hook_registry = hook_registry
    
    async def trigger_create(
        self,
        model: Any,
        context: Optional[HookContext] = None,
    ) -> None:
        """Trigger audit hook for CREATE operation.
        
        Args:
            model: The SQLAlchemy model instance that was created.
            context: Hook context with user and request information.
        """
        if context is None or self.hook_registry is None:
            logger.debug("No context or hook_registry provided for audit CREATE, skipping")
            return
        
        await self._trigger_hook(
            event=HookEvent.ON_MODEL_AFTER_CREATE,
            model=model,
            context=context,
        )
    
    async def trigger_update(
        self,
        model: Any,
        old_values: dict[str, Any],
        context: Optional[HookContext] = None,
    ) -> None:
        """Trigger audit hook for UPDATE operation.
        
        Args:
            model: The SQLAlchemy model instance that was updated.
            old_values: Dictionary of old values before the update.
            context: Hook context with user and request information.
        """
        if context is None or self.hook_registry is None:
            logger.debug("No context or hook_registry provided for audit UPDATE, skipping")
            return
        
        await self._trigger_hook(
            event=HookEvent.ON_MODEL_AFTER_UPDATE,
            model=model,
            context=context,
            old_values=old_values,
        )
    
    async def trigger_delete(
        self,
        model: Any,
        context: Optional[HookContext] = None,
    ) -> None:
        """Trigger audit hook for DELETE operation.
        
        Args:
            model: The SQLAlchemy model instance that was deleted.
            context: Hook context with user and request information.
        """
        if context is None or self.hook_registry is None:
            logger.debug("No context or hook_registry provided for audit DELETE, skipping")
            return
        
        await self._trigger_hook(
            event=HookEvent.ON_MODEL_AFTER_DELETE,
            model=model,
            context=context,
        )
    
    async def _trigger_hook(
        self,
        event: str,
        model: Any,
        context: HookContext,
        old_values: Optional[dict[str, Any]] = None,
    ) -> None:
        """Internal method to trigger audit hook.
        
        Args:
            event: Hook event name.
            model: SQLAlchemy model instance.
            context: Hook context.
            old_values: Optional dictionary of old values for UPDATE.
        """
        if self.hook_registry is None:
            return
        
        try:
            # Prepare data for hook
            data = {
                "model": model,
                "session": self.session,
            }
            
            if old_values:
                data["old_values"] = old_values
            
            # Trigger the hook
            await self.hook_registry.trigger(
                event=event,
                data=data,
                context=context,
            )
            
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(
                f"Failed to trigger audit hook for {event}",
                error=str(e),
                exc_info=True,
            )
    
    @staticmethod
    def capture_old_values(model: Any) -> dict[str, Any]:
        """Capture current values of a model before update.
        
        This should be called BEFORE modifying the model instance.
        
        Args:
            model: SQLAlchemy model instance.
        
        Returns:
            Dictionary mapping column names to their current values.
        """
        old_values = {}
        mapper = sqlalchemy_inspect(model.__class__)
        
        for column in mapper.columns:
            column_name = column.name
            value = getattr(model, column_name, None)
            
            # Convert to string for storage
            if value is not None:
                old_values[column_name] = str(value)
            else:
                old_values[column_name] = None
        
        return old_values
