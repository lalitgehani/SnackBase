"""Hook decorator API for user-friendly hook registration.

This module provides the decorator-based API for registering hooks,
enabling the `@app.hook.on_record_after_create("posts")` syntax.

IMPORTANT: This is a STABLE API. The decorator methods are part of
           the public API contract and cannot be changed.
"""

from typing import Any, Callable, Optional, TypeVar

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry

F = TypeVar("F", bound=Callable[..., Any])


class HookDecorator:
    """Provides decorator syntax for hook registration.

    This class wraps the HookRegistry and provides decorator methods
    for each hook event. It enables the user-friendly syntax:

        @app.hook.on_record_after_create("posts", priority=10)
        async def my_handler(event, data, context):
            return data

    Attributes:
        _registry: The underlying HookRegistry.

    Example:
        decorator = HookDecorator(registry)

        @decorator.on_record_after_create("posts")
        async def notify_on_post_create(event, data, context):
            await send_notification(data["created_by"])
            return data
    """

    def __init__(self, registry: HookRegistry) -> None:
        """Initialize with a HookRegistry.

        Args:
            registry: The HookRegistry to delegate to.
        """
        self._registry = registry

    @property
    def registry(self) -> HookRegistry:
        """Get the underlying hook registry."""
        return self._registry

    # =========================================================================
    # App Lifecycle Hooks
    # =========================================================================

    def on_bootstrap(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for application bootstrap.

        Called when the application is starting up, before serving requests.

        Args:
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_BOOTSTRAP,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_serve(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for when the application is ready to serve.

        Args:
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_SERVE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_terminate(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for application shutdown.

        Args:
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_TERMINATE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Record Operation Hooks
    # =========================================================================

    def on_record_before_create(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before record creation.

        Called before a record is created. Can modify data or abort.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.

        Example:
            @app.hook.on_record_before_create("posts")
            async def validate_post(event, data, context):
                if not data.get("title"):
                    raise AbortHookException("Title is required")
                return data
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_after_create(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after record creation.

        Called after a record is successfully created.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.

        Example:
            @app.hook.on_record_after_create("posts")
            async def notify_followers(event, data, context):
                await send_notification(data)
                return data
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_before_update(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before record update.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_after_update(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after record update.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_AFTER_UPDATE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_before_delete(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before record deletion.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_BEFORE_DELETE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_after_delete(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after record deletion.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_AFTER_DELETE,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_before_query(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before record query.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_BEFORE_QUERY,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_record_after_query(
        self,
        collection: Optional[str] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after record query.

        Args:
            collection: Optional collection name filter.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """
        return self._create_decorator(
            event=HookEvent.ON_RECORD_AFTER_QUERY,
            collection=collection,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Collection Operation Hooks
    # =========================================================================

    def on_collection_before_create(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before collection creation."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_BEFORE_CREATE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_collection_after_create(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after collection creation."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_AFTER_CREATE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_collection_before_update(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before collection update."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_BEFORE_UPDATE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_collection_after_update(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after collection update."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_AFTER_UPDATE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_collection_before_delete(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before collection deletion."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_BEFORE_DELETE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_collection_after_delete(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after collection deletion."""
        return self._create_decorator(
            event=HookEvent.ON_COLLECTION_AFTER_DELETE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Auth Operation Hooks
    # =========================================================================

    def on_auth_before_login(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before login."""
        return self._create_decorator(
            event=HookEvent.ON_AUTH_BEFORE_LOGIN,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_auth_after_login(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after login."""
        return self._create_decorator(
            event=HookEvent.ON_AUTH_AFTER_LOGIN,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_auth_before_register(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before registration."""
        return self._create_decorator(
            event=HookEvent.ON_AUTH_BEFORE_REGISTER,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_auth_after_register(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after registration."""
        return self._create_decorator(
            event=HookEvent.ON_AUTH_AFTER_REGISTER,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Request Processing Hooks
    # =========================================================================

    def on_before_request(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before request processing."""
        return self._create_decorator(
            event=HookEvent.ON_BEFORE_REQUEST,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_after_request(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after request processing."""
        return self._create_decorator(
            event=HookEvent.ON_AFTER_REQUEST,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Realtime Hooks
    # =========================================================================

    def on_realtime_connect(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for realtime connection."""
        return self._create_decorator(
            event=HookEvent.ON_REALTIME_CONNECT,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_realtime_disconnect(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for realtime disconnection."""
        return self._create_decorator(
            event=HookEvent.ON_REALTIME_DISCONNECT,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_realtime_message(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for realtime messages."""
        return self._create_decorator(
            event=HookEvent.ON_REALTIME_MESSAGE,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Mailer Hooks
    # =========================================================================

    def on_mailer_before_send(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for before email send."""
        return self._create_decorator(
            event=HookEvent.ON_MAILER_BEFORE_SEND,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def on_mailer_after_send(
        self,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> Callable[[F], F]:
        """Register a hook for after email send."""
        return self._create_decorator(
            event=HookEvent.ON_MAILER_AFTER_SEND,
            collection=None,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    # =========================================================================
    # Generic Registration
    # =========================================================================

    def register(
        self,
        event: str,
        callback: Callable,
        filters: Optional[dict[str, Any]] = None,
        priority: int = 0,
        stop_on_error: bool = False,
    ) -> str:
        """Register a hook directly (non-decorator style).

        This is the same as calling registry.register() directly.

        Args:
            event: Hook event name.
            callback: Async function to execute.
            filters: Optional tag-based filters.
            priority: Execution priority (higher = earlier).
            stop_on_error: Abort chain on error.

        Returns:
            Unique hook_id for later removal.
        """
        return self._registry.register(
            event=event,
            callback=callback,
            filters=filters,
            priority=priority,
            stop_on_error=stop_on_error,
        )

    def unregister(self, hook_id: str) -> bool:
        """Unregister a hook by ID.

        Args:
            hook_id: The unique hook ID.

        Returns:
            True if removed, False if not found or built-in.
        """
        return self._registry.unregister(hook_id)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _create_decorator(
        self,
        event: str,
        collection: Optional[str],
        priority: int,
        stop_on_error: bool,
    ) -> Callable[[F], F]:
        """Create a decorator function for registering hooks.

        Args:
            event: Hook event name.
            collection: Optional collection filter.
            priority: Execution priority.
            stop_on_error: Abort chain on error.

        Returns:
            Decorator function.
        """

        def decorator(func: F) -> F:
            filters = {}
            if collection:
                filters["collection"] = collection

            self._registry.register(
                event=event,
                callback=func,
                filters=filters,
                priority=priority,
                stop_on_error=stop_on_error,
            )
            return func

        return decorator
