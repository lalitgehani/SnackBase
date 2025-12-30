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
from snackbase.infrastructure.auth.jwt_service import jwt_service

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
        
        # Try to enrich with user info from JWT
        # We don't fail here if auth is invalid - that's for the auth dependency
        # We just want best-effort context for logging/audit
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = jwt_service.decode_token(token)
                
                # Create a minimal user object for context
                # This avoids a DB hit but gives us enough for audit logs
                from dataclasses import dataclass
                
                @dataclass
                class ContextUser:
                    id: str
                    email: str
                    account_id: str
                    role: str
                
                user = ContextUser(
                    id=payload.get("user_id", ""),
                    email=payload.get("email", ""),
                    account_id=payload.get("account_id", ""),
                    role=payload.get("role", ""),
                )
                
                context.user = user  # type: ignore # Duck typing compatible
                context.account_id = user.account_id
                context.user_name = getattr(user, "name", user.email)
                
            except Exception as e:
                # Log debug but continue - this might be an invalid token request
                # that will be rejected by the endpoint anyway
                logger.debug("Context middleware: Failed to extract user context", error=str(e))

        # Set globally
        set_current_context(context)

        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup to prevent context leakage
            clear_current_context()
