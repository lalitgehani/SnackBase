"""Hook system core module.

This module provides the hook system infrastructure for SnackBase.
It enables extensibility through event-based hooks that can be
registered via decorators or programmatically.

IMPORTANT: This is a STABLE API CONTRACT. The public interfaces in
           this module should not have breaking changes.

Example usage:
    from snackbase.core.hooks import HookRegistry, HookDecorator, HookEvent

    registry = HookRegistry()
    hook = HookDecorator(registry)

    @hook.on_record_after_create("posts")
    async def notify_on_post(event, data, context):
        await send_notification(data)
        return data

    # Or via the app:
    @app.hook.on_record_after_create("posts")
    async def notify_on_post(event, data, context):
        await send_notification(data)
        return data
"""

from snackbase.core.hooks.hook_decorator import HookDecorator
from snackbase.core.hooks.hook_events import (
    EVENT_CATEGORIES,
    HookCategory,
    HookEvent,
    get_all_events,
    is_after_event,
    is_before_event,
)
from snackbase.core.hooks.hook_registry import HookRegistry, RegisteredHook

__all__ = [
    # Registry
    "HookRegistry",
    "RegisteredHook",
    # Decorator
    "HookDecorator",
    # Events
    "HookCategory",
    "HookEvent",
    "EVENT_CATEGORIES",
    "get_all_events",
    "is_before_event",
    "is_after_event",
]
