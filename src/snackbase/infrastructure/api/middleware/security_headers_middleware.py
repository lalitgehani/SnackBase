"""Security headers middleware for SnackBase.

This middleware adds security headers to all HTTP responses to protect
against common web vulnerabilities including XSS, clickjacking, and
MIME type sniffing attacks.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import RedirectResponse

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.
    
    This middleware implements defense-in-depth security by adding multiple
    security headers that instruct browsers to enforce security policies.
    
    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables browser XSS protection
    - Strict-Transport-Security: Enforces HTTPS (production only)
    - Content-Security-Policy: Prevents XSS and injection attacks
    - Permissions-Policy: Restricts browser features
    - Referrer-Policy: Controls referrer information
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and add security headers to the response.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint to call.

        Returns:
            The response with security headers added.
        """
        settings = get_settings()

        # Skip if security headers are disabled
        if not settings.security_headers_enabled:
            return await call_next(request)

        # Check if HTTPS redirect is needed (production only)
        if (
            settings.is_production
            and settings.https_redirect_enabled
            and request.url.scheme == "http"
        ):
            # Redirect HTTP to HTTPS
            https_url = request.url.replace(scheme="https")
            logger.info(
                "Redirecting HTTP to HTTPS",
                original_url=str(request.url),
                redirect_url=str(https_url),
            )
            return RedirectResponse(url=str(https_url), status_code=301)

        # Process the request
        response = await call_next(request)

        # Add security headers
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking by denying iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # Enable browser XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add HSTS header in production only
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.hsts_max_age}; includeSubDomains"
            )

        # Content Security Policy - prevents XSS and injection attacks
        response.headers["Content-Security-Policy"] = settings.csp_policy

        # Permissions Policy - restricts browser features
        response.headers["Permissions-Policy"] = settings.permissions_policy

        # Referrer Policy - controls referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
