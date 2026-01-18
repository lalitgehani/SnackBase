"""Unit tests for rate limit middleware.

These tests verify the RateLimitMiddleware behavior including IP-based limiting,
user-based limiting, superadmin bypass, and rate limit headers.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from snackbase.infrastructure.api.middleware.rate_limit_middleware import RateLimitMiddleware
from snackbase.infrastructure.api.middleware.rate_limit_storage import RateLimitStorage
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.domain.entities.hook_context import HookContext


def create_test_app(settings_patch=None) -> FastAPI:
    """Create a test FastAPI app with rate limit middleware."""
    app = FastAPI()
    
    # Mock settings if provided
    if settings_patch:
        with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings") as mock_settings:
            mock_settings.return_value = settings_patch
            app.add_middleware(RateLimitMiddleware)
    else:
        app.add_middleware(RateLimitMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    return app


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.rate_limit_enabled = True
    settings.rate_limit_per_minute = 5
    settings.rate_limit_authenticated_per_minute = 10
    settings.rate_limit_burst = 2
    settings.rate_limit_endpoints = {}
    return settings


def test_rate_limit_headers_present(mock_settings):
    """Verify rate limit headers are added to the response."""
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        # Reset storage to ensures clean state
        from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
        rate_limit_storage._storage = {}
        
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "5"


def test_rate_limit_exceeded(mock_settings):
    """Verify 429 is returned when rate limit is exceeded."""
    mock_settings.rate_limit_per_minute = 1
    mock_settings.rate_limit_burst = 1
    
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
        rate_limit_storage._storage = {}
        
        app = create_test_app()
        client = TestClient(app)
        
        # First request - OK
        response = client.get("/test")
        assert response.status_code == 200
        
        # Second request - Rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["error"] == "Too Many Requests"


def test_superadmin_bypass(mock_settings):
    """Verify superadmins bypass the rate limit."""
    mock_settings.rate_limit_per_minute = 1
    mock_settings.rate_limit_burst = 1
    
    # Mock context to return a superadmin user
    mock_user = MagicMock()
    mock_user.id = "admin-1"
    
    mock_context = MagicMock(spec=HookContext)
    mock_context.user = mock_user
    mock_context.account_id = SYSTEM_ACCOUNT_ID
    
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_current_context", return_value=mock_context):
            from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
            rate_limit_storage._storage = {}
            
            app = create_test_app()
            client = TestClient(app)
            
            # Multiple requests should all succeed
            for _ in range(3):
                response = client.get("/test")
                assert response.status_code == 200


def test_user_based_limit(mock_settings):
    """Verify authenticated users get a higher rate limit."""
    mock_settings.rate_limit_per_minute = 1
    mock_settings.rate_limit_authenticated_per_minute = 3
    mock_settings.rate_limit_burst = 3
    
    mock_user = MagicMock()
    mock_user.id = "user-123"
    
    mock_context = MagicMock(spec=HookContext)
    mock_context.user = mock_user
    mock_context.account_id = "some-account"
    
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_current_context", return_value=mock_context):
            from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
            rate_limit_storage._storage = {}
            
            app = create_test_app()
            client = TestClient(app)
            
            # Should allow 3 requests (burst=3)
            for _ in range(3):
                response = client.get("/test")
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Limit"] == "3"
            
            # 4th should fail
            response = client.get("/test")
            assert response.status_code == 429


def test_rate_limit_disabled(mock_settings):
    """Verify middleware does nothing when disabled."""
    mock_settings.rate_limit_enabled = False
    mock_settings.rate_limit_per_minute = 1
    mock_settings.rate_limit_burst = 1
    
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
        rate_limit_storage._storage = {}
        
        app = create_test_app()
        client = TestClient(app)
        
        # Multiple requests should succeed
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers


def test_endpoint_override(mock_settings):
    """Verify endpoint-specific overrides work."""
    mock_settings.rate_limit_per_minute = 10
    mock_settings.rate_limit_endpoints = {"/test": 1}
    mock_settings.rate_limit_burst = 1
    
    with patch("snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings", return_value=mock_settings):
        from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage
        rate_limit_storage._storage = {}
        
        app = create_test_app()
        client = TestClient(app)
        
        # /test should be limited to 1
        response = client.get("/test")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "1"
        
        response = client.get("/test")
        assert response.status_code == 429
