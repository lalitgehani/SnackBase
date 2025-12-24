"""Hook registry - Central hook registration and execution engine.

The HookRegistry is the core of the hook system. It provides:
- Registration of hooks with filters and priority
- Execution of hooks in priority order
- Tag-based filtering for collection-specific hooks
- Error handling and logging

IMPORTANT: This is a STABLE API. Changes to the registration interface
           would be breaking changes for users who have built plugins.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import (
    AbortHookException,
    HookContext,
    HookResult,
)

logger = get_logger(__name__)


@dataclass
class RegisteredHook:
    """Internal representation of a registered hook.

    Attributes:
        id: Unique identifier for this hook registration.
        event: The event this hook is registered for.
        callback: The async function to call.
        filters: Tag-based filters (e.g., {"collection": "posts"}).
        priority: Execution priority (higher = earlier).
        stop_on_error: Whether errors should abort the chain.
        is_builtin: Whether this is a built-in system hook.
        registration_order: Order in which this hook was registered.
    """

    id: str
    event: str
    callback: Callable
    filters: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    stop_on_error: bool = False
    is_builtin: bool = False
    registration_order: int = 0


class HookRegistry:
    """Central hook registration and execution engine.

    This class manages all hook registrations and provides methods
    to trigger hooks with proper filtering, ordering, and error handling.

    The registry is a stable API contract - changes to the registration
    mechanism would be breaking changes for all users.

    Example:
        registry = HookRegistry()

        # Register a hook
        hook_id = registry.register(
            event="on_record_after_create",
            callback=my_handler,
            filters={"collection": "posts"},
            priority=10,
        )

        # Trigger hooks for an event
        result = await registry.trigger(
            event="on_record_after_create",
            data={"title": "Hello"},
            context=hook_context,
            filters={"collection": "posts"},
        )

        # Unregister a hook
        registry.unregister(hook_id)
    """

    def __init__(self) -> None:
        """Initialize the hook registry."""
        self._hooks: dict[str, list[RegisteredHook]] = {}
        self._registration_counter: int = 0
        self._hook_map: dict[str, RegisteredHook] = {}  # hook_id -> hook

    def register(
        self,
        event: str,
        callback: Callable,
        filters: Optional[dict[str, Any]] = None,
        priority: int = 0,
        stop_on_error: bool = False,
        is_builtin: bool = False,
    ) -> str:
        """Register a hook for an event.

        Args:
            event: Hook event name (e.g., "on_record_after_create").
            callback: Async function to execute. Should accept
                      (event, data, context) and return modified data.
            filters: Optional tag-based filters. Hook only fires if
                     all filter conditions match (e.g., {"collection": "posts"}).
            priority: Execution priority. Higher priority hooks run first.
                      Default is 0. Built-in hooks use negative priorities.
            stop_on_error: If True, errors in this hook abort the chain.
                           Default is False (errors are logged but continue).
            is_builtin: If True, this hook cannot be unregistered.

        Returns:
            Unique hook_id string for later removal.

        Example:
            hook_id = registry.register(
                event="on_record_after_create",
                callback=async def (event, data, ctx): return data,
                filters={"collection": "posts"},
                priority=10,
            )
        """
        hook_id = f"hook_{uuid.uuid4().hex[:12]}"

        # Increment registration counter for FIFO ordering within same priority
        self._registration_counter += 1

        hook = RegisteredHook(
            id=hook_id,
            event=event,
            callback=callback,
            filters=filters or {},
            priority=priority,
            stop_on_error=stop_on_error,
            is_builtin=is_builtin,
            registration_order=self._registration_counter,
        )

        # Add to event list
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)

        # Add to lookup map
        self._hook_map[hook_id] = hook

        logger.debug(
            "Hook registered",
            hook_id=hook_id,
            hook_event=event,
            priority=priority,
            filters=filters,
            is_builtin=is_builtin,
        )

        return hook_id

    def unregister(self, hook_id: str) -> bool:
        """Remove a registered hook.

        Args:
            hook_id: The unique ID returned from register().

        Returns:
            True if hook was removed, False if not found or is built-in.

        Note:
            Built-in hooks (is_builtin=True) cannot be unregistered.
        """
        hook = self._hook_map.get(hook_id)
        if not hook:
            logger.warning("Hook not found for unregister", hook_id=hook_id)
            return False

        if hook.is_builtin:
            logger.warning(
                "Cannot unregister built-in hook",
                hook_id=hook_id,
                hook_event=hook.event,
            )
            return False

        # Remove from event list
        if hook.event in self._hooks:
            self._hooks[hook.event] = [
                h for h in self._hooks[hook.event] if h.id != hook_id
            ]
            # Clean up empty event lists
            if not self._hooks[hook.event]:
                del self._hooks[hook.event]

        # Remove from lookup map
        del self._hook_map[hook_id]

        logger.debug("Hook unregistered", hook_id=hook_id, hook_event=hook.event)

        return True

    async def trigger(
        self,
        event: str,
        data: Optional[dict[str, Any]] = None,
        context: Optional[HookContext] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> HookResult:
        """Execute all registered hooks for an event.

        Hooks are executed in priority order (higher priority first).
        Hooks with the same priority execute in registration order (FIFO).

        Args:
            event: Hook event name.
            data: Data to pass to hooks. For before_* events, this can
                  be modified by hooks and the modified data is returned.
            context: HookContext with app, user, and request info.
            filters: Trigger-time filters. Only hooks matching these
                     filters will be executed.

        Returns:
            HookResult with success status, any errors, and final data.

        Example:
            result = await registry.trigger(
                event="on_record_before_create",
                data={"title": "Hello"},
                context=hook_context,
                filters={"collection": "posts"},
            )
            if result.aborted:
                raise HTTPException(result.abort_status_code, result.abort_message)
            data = result.data  # Use modified data
        """
        result = HookResult(success=True, data=data)

        # Get hooks for this event
        hooks = self._hooks.get(event, [])
        if not hooks:
            return result

        # Filter hooks based on trigger filters
        matching_hooks = self._filter_hooks(hooks, filters)
        if not matching_hooks:
            return result

        # Sort by priority (descending), then registration order (ascending)
        sorted_hooks = sorted(
            matching_hooks,
            key=lambda h: (-h.priority, h.registration_order),
        )

        logger.debug(
            "Triggering hooks",
            hook_event=event,
            hook_count=len(sorted_hooks),
            filters=filters,
        )

        # Execute hooks in order
        current_data = data
        for hook in sorted_hooks:
            try:
                # Call the hook
                hook_result = await self._execute_hook(hook, event, current_data, context)

                # Update data if hook returned modified data
                if hook_result is not None and isinstance(hook_result, dict):
                    current_data = hook_result
                    result.data = current_data

            except AbortHookException as e:
                # Hook wants to abort the operation
                logger.info(
                    "Hook aborted operation",
                    hook_id=hook.id,
                    hook_event=event,
                    message=e.message,
                    status_code=e.status_code,
                )
                result.success = False
                result.aborted = True
                result.abort_message = e.message
                result.abort_status_code = e.status_code
                return result

            except Exception as e:
                # Log error but continue (unless stop_on_error)
                error_msg = f"Hook {hook.id} failed: {str(e)}"
                logger.error(
                    "Hook execution failed",
                    hook_id=hook.id,
                    hook_event=event,
                    error=str(e),
                    stop_on_error=hook.stop_on_error,
                )
                result.errors.append(error_msg)

                if hook.stop_on_error:
                    result.success = False
                    return result

        return result

    async def _execute_hook(
        self,
        hook: RegisteredHook,
        event: str,
        data: Optional[dict[str, Any]],
        context: Optional[HookContext],
    ) -> Any:
        """Execute a single hook callback.

        Args:
            hook: The registered hook to execute.
            event: Event name being triggered.
            data: Data to pass to the hook.
            context: HookContext for the hook.

        Returns:
            The return value of the hook callback.
        """
        callback = hook.callback

        # Check if callback is coroutine
        if asyncio.iscoroutinefunction(callback):
            return await callback(event, data, context)
        else:
            # Wrap sync functions in executor
            # But we really want async-only for FastAPI
            logger.warning(
                "Hook callback is not async, wrapping",
                hook_id=hook.id,
                hook_event=event,
            )
            return callback(event, data, context)

    def _filter_hooks(
        self,
        hooks: list[RegisteredHook],
        filters: Optional[dict[str, Any]],
    ) -> list[RegisteredHook]:
        """Filter hooks based on trigger filters.

        A hook matches if:
        - It has no filters (matches everything), OR
        - All its filter keys match the trigger filters

        Args:
            hooks: List of registered hooks.
            filters: Trigger-time filters.

        Returns:
            List of matching hooks.
        """
        if not filters:
            # No trigger filters, return all hooks
            return hooks

        matching = []
        for hook in hooks:
            if not hook.filters:
                # Hook with no filters matches everything
                matching.append(hook)
                continue

            # Check if all hook filters match trigger filters
            matches = True
            for key, value in hook.filters.items():
                trigger_value = filters.get(key)
                if trigger_value is None:
                    # Trigger doesn't have this filter, hook doesn't match
                    matches = False
                    break
                if value != trigger_value:
                    # Values don't match
                    matches = False
                    break

            if matches:
                matching.append(hook)

        return matching

    def get_hooks_for_event(self, event: str) -> list[RegisteredHook]:
        """Get all hooks registered for an event.

        Args:
            event: Event name.

        Returns:
            List of registered hooks for the event.
        """
        return self._hooks.get(event, []).copy()

    def get_all_hooks(self) -> dict[str, list[RegisteredHook]]:
        """Get all registered hooks organized by event.

        Returns:
            Dictionary mapping event names to lists of hooks.
        """
        return {event: hooks.copy() for event, hooks in self._hooks.items()}

    def get_hook_by_id(self, hook_id: str) -> Optional[RegisteredHook]:
        """Get a hook by its ID.

        Args:
            hook_id: The unique hook ID.

        Returns:
            The RegisteredHook or None if not found.
        """
        return self._hook_map.get(hook_id)

    def clear(self, include_builtin: bool = False) -> int:
        """Remove all registered hooks.

        Args:
            include_builtin: If True, also remove built-in hooks.
                             Default is False (preserve built-in hooks).

        Returns:
            Number of hooks removed.
        """
        count = 0

        if include_builtin:
            count = len(self._hook_map)
            self._hooks.clear()
            self._hook_map.clear()
        else:
            # Keep only built-in hooks
            to_remove = [
                hook_id
                for hook_id, hook in self._hook_map.items()
                if not hook.is_builtin
            ]
            for hook_id in to_remove:
                self.unregister(hook_id)
                count += 1

        logger.debug("Hooks cleared", count=count, include_builtin=include_builtin)
        return count
