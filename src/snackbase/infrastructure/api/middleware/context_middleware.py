"""Middleware for managing request context.

This middleware extracts user information from the Authorization header
and initializes the global HookContext, ensuring it's available for
event listeners and other components throughout the request lifecycle.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from snackbase.core.context import clear_current_context, set_current_context
from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)


class ContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set up global HookContext for every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and setup context.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint to call.

        Returns:
            The response from the application.
        """
        # Create base context (anonymous)
        context = HookContext(
            app=request.app,
            request=request,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Try to enrich with user info from AuthenticationMiddleware
        if hasattr(request.state, "authenticated_user"):
            auth_user = request.state.authenticated_user
            context.user = auth_user
            context.account_id = auth_user.account_id
            context.user_name = auth_user.email

        # Set globally
        set_current_context(context)

        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup to prevent context leakage
            clear_current_context()
