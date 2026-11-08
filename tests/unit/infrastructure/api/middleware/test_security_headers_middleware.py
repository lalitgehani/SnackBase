"""Unit tests for security headers middleware.

These tests verify the SecurityHeadersMiddleware behavior in isolation,
including production mode HSTS headers and HTTPS redirect functionality.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from snackbase.infrastructure.api.middleware.security_headers_middleware import (
    SecurityHeadersMiddleware,
    csp_for_docs,
)


def create_test_app(environment: str = "development", https_redirect: bool = False) -> FastAPI:
    """Create a test FastAPI app with security headers middleware.

    Args:
        environment: Environment mode (development/production)
        https_redirect: Whether to enable HTTPS redirect

    Returns:
        FastAPI app with middleware configured
    """
    app = FastAPI()

    # Mock settings
    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = (environment == "production")
        settings.hsts_max_age = 31536000
        settings.csp_policy = "default-src 'self'; script-src 'self'"
        settings.permissions_policy = "geolocation=(), camera=()"
        settings.https_redirect_enabled = https_redirect

        app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


def test_hsts_header_in_production():
    """Verify HSTS header is added in production mode."""
    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = True
        settings.hsts_max_age = 31536000
        settings.csp_policy = "default-src 'self'"
        settings.permissions_policy = "geolocation=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_no_hsts_in_development():
    """Verify HSTS header is NOT added in development mode."""
    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = False
        settings.hsts_max_age = 31536000
        settings.csp_policy = "default-src 'self'"
        settings.permissions_policy = "geolocation=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers


def test_security_headers_disabled():
    """Verify middleware can be disabled via configuration."""
    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Headers should not be added when disabled
        assert "X-Content-Type-Options" not in response.headers
        assert "X-Frame-Options" not in response.headers


def test_all_security_headers_present():
    """Verify all security headers are added to responses."""
    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = False
        settings.hsts_max_age = 31536000
        settings.csp_policy = "default-src 'self'; script-src 'self'"
        settings.permissions_policy = "geolocation=(), camera=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200

        # Verify all expected headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Content-Security-Policy"] == "default-src 'self'; script-src 'self'"
        assert response.headers["Permissions-Policy"] == "geolocation=(), camera=()"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_custom_csp_policy():
    """Verify CSP policy can be customized via configuration."""
    custom_csp = "default-src 'none'; script-src 'self' https://cdn.example.com"

    with patch("snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = False
        settings.hsts_max_age = 31536000
        settings.csp_policy = custom_csp
        settings.permissions_policy = "geolocation=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["Content-Security-Policy"] == custom_csp


def test_swagger_cdn_is_allowed_on_docs_routes():
    """Swagger UI must be able to load its scripts and styles from its CDN."""
    policy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"

    with patch(
        "snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings"
    ) as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = False
        settings.hsts_max_age = 31536000
        settings.csp_policy = policy
        settings.permissions_policy = "geolocation=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/docs")
        async def docs():
            return {"docs": True}

        @app.get("/docs/oauth2-redirect")
        async def oauth2_redirect():
            return {"redirect": True}

        client = TestClient(app)

        for path in ("/docs", "/docs/oauth2-redirect"):
            response = client.get(path)
            assert response.status_code == 200
            csp = response.headers["Content-Security-Policy"]
            assert "script-src 'self' https://cdn.jsdelivr.net" in csp
            assert (
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
                "https://fonts.googleapis.com"
            ) in csp
            assert "img-src https://cdn.jsdelivr.net" in csp
            assert "font-src https://cdn.jsdelivr.net https://fonts.gstatic.com" in csp
            assert "default-src 'self'" in csp


def test_swagger_cdn_is_not_allowed_on_other_routes():
    """The relaxation must never leak onto API or admin responses."""
    policy = "default-src 'self'; script-src 'self'"

    with patch(
        "snackbase.infrastructure.api.middleware.security_headers_middleware.get_settings"
    ) as mock_settings:
        settings = mock_settings.return_value
        settings.security_headers_enabled = True
        settings.is_production = False
        settings.hsts_max_age = 31536000
        settings.csp_policy = policy
        settings.permissions_policy = "geolocation=()"
        settings.https_redirect_enabled = False

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["Content-Security-Policy"] == policy


def test_csp_for_docs_does_not_duplicate_origins():
    """A policy that already allows the CDN keeps a single occurrence per directive."""
    policy = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net"

    csp = csp_for_docs(policy)

    assert csp.count("https://cdn.jsdelivr.net") == 4
