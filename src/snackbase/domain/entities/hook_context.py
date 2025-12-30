"""Hook context and exceptions for the hook system.

Contains the core data structures used by the hook system:
- HookContext: Context passed to all hook callbacks
- AbortHookException: Raised by before-hooks to cancel operations
- HookResult: Result of a hook trigger operation
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from starlette.requests import Request

    from snackbase.domain.entities.user import User


class AbortHookException(Exception):
    """Raised by before-hooks to cancel an operation.

    When raised in a before-hook, the operation will be cancelled
    and an appropriate error response will be returned to the client.

    Args:
        message: Human-readable error message.
        status_code: HTTP status code to return (default: 400 Bad Request).

    Example:
        @app.hook.on_record_before_create("orders")
        async def validate_order(event, data, context):
            if data.get("total", 0) < 0:
                raise AbortHookException("Order total cannot be negative", 400)
            return data
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class HookContext:
    """Context passed to all hook callbacks.

    This object provides hooks with access to the current execution context,
    including the authenticated user, account, and request information.

    Attributes:
        app: The SnackBase application instance.
        user: The authenticated user, or None for anonymous requests.
        account_id: The current account context ID.
        request_id: Correlation ID for logging and tracing.
        request: The FastAPI/Starlette Request object.

    Example:
        async def my_hook(event: str, data: dict, context: HookContext) -> dict:
            if context.user:
                logger.info(f"User {context.user.email} triggered {event}")
            return data
    """

    app: Any  # Avoid circular import - will be SnackBase app
    user: Optional["User"] = None
    account_id: Optional[str] = None
    request_id: str = ""
    request: Optional["Request"] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate context after initialization."""
        if not self.request_id:
            import uuid

            self.request_id = f"hk_{uuid.uuid4().hex[:12]}"


@dataclass
class HookResult:
    """Result of a hook trigger operation.

    Attributes:
        success: Whether all hooks executed successfully.
        aborted: Whether the operation was aborted by a hook.
        abort_message: Message from AbortHookException if aborted.
        abort_status_code: Status code from AbortHookException if aborted.
        errors: List of error messages from hooks that failed.
        data: Modified data from the hook chain.
    """

    success: bool = True
    aborted: bool = False
    abort_message: Optional[str] = None
    abort_status_code: int = 400
    errors: list[str] = field(default_factory=list)
    data: Optional[dict[str, Any]] = None
