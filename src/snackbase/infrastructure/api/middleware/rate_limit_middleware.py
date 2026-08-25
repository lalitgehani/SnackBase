"""Rate limiting middleware for SnackBase.

This middleware protects the API from abuse by limiting the number of requests
from a specific IP address or authenticated user within a time window.

Only paths under ``settings.api_prefix`` are metered. Everything the limiter
needs to protect lives there — the auth routes, the record CRUD, the custom
endpoint and function dispatchers, and the workflow webhooks — while the SPA
catch-all serves every *other* path, so a static allowlist could never be
complete. The deliberate tradeoff is that static asset serving is unmetered at
the application layer: assets ship with ``cache-control: max-age=14400`` and are
meant to be absorbed by a CDN or reverse proxy, and the SPA handler's
path-traversal guard remains the security boundary for that route. Metering them
here bought nothing and cost the demo its front page, because a single cold page
load spent the whole bucket before the SPA had booted.

Health checks (``/health``, ``/ready``, ``/live``) fall outside the prefix and
are exempt by the same rule, with no special case of their own.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from snackbase.core.config import get_settings
from snackbase.core.context import get_current_context
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.api.middleware.client_ip import get_client_ip
from snackbase.infrastructure.api.middleware.rate_limit_storage import (
    compute_capacity,
    rate_limit_storage,
)

logger = get_logger(__name__)


def _is_api_path(path: str, api_prefix: str) -> bool:
    """Return whether a request path falls under the API prefix.

    Matches on a segment boundary, the same way the SPA catch-all's API guard
    does, so ``/api/v1x/foo`` is not mistaken for an API path.

    Args:
        path: The request path.
        api_prefix: The configured API prefix, e.g. ``/api/v1``.

    Returns:
        True when the path is the prefix itself or sits beneath it.
    """
    prefix = api_prefix.rstrip("/")
    return path == prefix or path.startswith(f"{prefix}/")


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

        path = request.url.path

        # Meter API traffic only. Checked before any context or client-IP work so
        # that an exempt request does no limiter work at all.
        if not _is_api_path(path, settings.api_prefix):
            return await call_next(request)

        # Get current context (set by ContextMiddleware)
        context = get_current_context()

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
        burst_multiplier = settings.rate_limit_burst_multiplier
        capacity = compute_capacity(rate, burst_multiplier)
        is_allowed, remaining, reset_seconds = rate_limit_storage.consume(
            key, rate, burst_multiplier=burst_multiplier
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
                    "X-RateLimit-Burst": str(int(capacity)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_seconds)),
                },
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate)
        response.headers["X-RateLimit-Burst"] = str(int(capacity))
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_seconds))

        return response
