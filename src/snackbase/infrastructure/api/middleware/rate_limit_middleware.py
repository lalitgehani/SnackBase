"""Rate limiting middleware for SnackBase.

This middleware protects the API from abuse by limiting the number of requests
from a specific IP address or authenticated user within a time window.
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from snackbase.core.config import get_settings
from snackbase.core.context import get_current_context
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.middleware.client_ip import get_client_ip
from snackbase.infrastructure.api.middleware.rate_limit_storage import rate_limit_storage
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and enforce rate limits.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint to call.

        Returns:
            The response from the application or a 429 error.
        """
        settings = get_settings()

        # Skip if rate limiting is disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Get current context (set by ContextMiddleware)
        context = get_current_context()

        path = request.url.path

        # Determine tracking key and limit
        # Default to IP-based tracking, honouring X-Forwarded-For from trusted proxies
        # so that clients behind one do not share a single bucket.
        key = f"ip:{get_client_ip(request)}"
        rate = settings.rate_limit_per_minute

        # Check if user is authenticated and not a superadmin
        if context and context.user:
            # Superadmin bypass — but never on the auth endpoints. Login is
            # unauthenticated, so a caller could otherwise present a superadmin
            # bearer token alongside a login body and buy an exemption from the
            # very limit that bounds password guessing.
            if context.account_id == SYSTEM_ACCOUNT_ID and not path.startswith("/api/v1/auth/"):
                return await call_next(request)

            # User-based tracking for authenticated users
            key = f"user:{context.user.id}"
            rate = settings.rate_limit_authenticated_per_minute

        # Check for endpoint-specific overrides
        # This is a simplified version, ideally we'd use a better path matching
        if path in settings.rate_limit_endpoints:
            rate = settings.rate_limit_endpoints[path]

        # Check rate limit
        is_allowed, remaining, reset_seconds = rate_limit_storage.consume(
            key, rate, burst=settings.rate_limit_burst
        )

        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                key=key,
                path=path,
                rate=rate,
                retry_after=int(reset_seconds),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Try again in {int(reset_seconds)} seconds.",
                },
                headers={
                    "Retry-After": str(int(reset_seconds)),
                    "X-RateLimit-Limit": str(rate),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_seconds)),
                },
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_seconds))

        return response
