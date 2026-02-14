"""Authentication middleware for SnackBase.

This middleware handles unified authentication for all token types:
- Standard JWT Bearer tokens
- SnackBase tokens (sb_ak, sb_pt, sb_ot)
- Legacy API keys (sb_sk)

It enriches the request state with the authenticated user context.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth.authenticator import Authenticator
from snackbase.infrastructure.auth.token_codec import AuthenticationError
from snackbase.infrastructure.persistence.database import get_db_manager

logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate ALL requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Authenticate the request and enrich request state.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint to call.

        Returns:
            The response from the application.
        """
        # Skip health endpoints
        if request.url.path in ["/health", "/ready", "/live"]:
            return await call_next(request)

        # Get database session factory
        db_manager = get_db_manager()
        session_factory = db_manager.session_factory
        
        authenticator = Authenticator()
        
        try:
            # We need a session for revocation check and legacy keys
            async with session_factory() as session:
                auth_user = await authenticator.authenticate(request.headers, session)
            
            # Set request.state.authenticated_user
            request.state.authenticated_user = auth_user
            
        except AuthenticationError as e:
            # We log the error but let the request proceed.
            # Dependencies or late logic will return 401 if needed.
            logger.debug(
                "Authentication failed in middleware", 
                error=str(e), 
                path=request.url.path
            )
        except Exception as e:
            # Handle unexpected errors gracefully
            logger.error(
                "Unexpected error in AuthenticationMiddleware", 
                error=str(e), 
                path=request.url.path
            )

        return await call_next(request)
