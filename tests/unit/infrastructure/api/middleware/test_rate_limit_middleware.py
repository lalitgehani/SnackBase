"""Unit tests for rate limit middleware.

These tests verify the RateLimitMiddleware behavior including IP-based limiting,
user-based limiting, superadmin bypass, rate limit headers, and the API-prefix
scope that keeps SPA and health traffic out of the limiter entirely.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.api.middleware.rate_limit_middleware import RateLimitMiddleware

API_PATH = "/api/v1/test"


def create_test_app() -> FastAPI:
    """Create a test FastAPI app with rate limit middleware."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get(API_PATH)
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/api/v1")
    async def api_root():
        return {"message": "root"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/assets/app.js")
    async def asset():
        return {"message": "asset"}

    @app.get("/api/v1x/foo")
    async def lookalike():
        return {"message": "lookalike"}

    return app


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.rate_limit_enabled = True
    settings.rate_limit_per_minute = 5
    settings.rate_limit_authenticated_per_minute = 10
    settings.rate_limit_burst_multiplier = 1.0
    settings.rate_limit_endpoints = {}
    settings.api_prefix = "/api/v1"
    return settings


@pytest.fixture
def clean_storage():
    from snackbase.infrastructure.api.middleware.rate_limit_middleware import rate_limit_storage

    rate_limit_storage.reset()
    yield rate_limit_storage
    rate_limit_storage.reset()


def _patch_settings(settings):
    return patch(
        "snackbase.infrastructure.api.middleware.rate_limit_middleware.get_settings",
        return_value=settings,
    )


def test_rate_limit_headers_present(mock_settings, clean_storage):
    """Verify rate limit headers are added to the response."""
    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        response = client.get(API_PATH)

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Burst"] == "5"
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


def test_rate_limit_exceeded(mock_settings, clean_storage):
    """Verify 429 is returned when rate limit is exceeded."""
    mock_settings.rate_limit_per_minute = 1

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        assert client.get(API_PATH).status_code == 200

        response = client.get(API_PATH)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Burst"] == "1"
        assert response.json()["error"] == "Too Many Requests"


def test_burst_multiplier_scales_capacity(mock_settings, clean_storage):
    """A multiplier of 2.0 doubles the number of requests allowed in a burst."""
    mock_settings.rate_limit_per_minute = 5
    mock_settings.rate_limit_burst_multiplier = 2.0

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        first = client.get(API_PATH)
        assert first.headers["X-RateLimit-Burst"] == "10"

        for _ in range(9):
            assert client.get(API_PATH).status_code == 200

        assert client.get(API_PATH).status_code == 429


def test_superadmin_bypass(mock_settings, clean_storage):
    """Verify superadmins bypass the rate limit."""
    mock_settings.rate_limit_per_minute = 1

    mock_user = MagicMock()
    mock_user.id = "admin-1"

    mock_context = MagicMock(spec=HookContext)
    mock_context.user = mock_user
    mock_context.account_id = SYSTEM_ACCOUNT_ID

    with _patch_settings(mock_settings), patch(
        "snackbase.infrastructure.api.middleware.rate_limit_middleware.get_current_context",
        return_value=mock_context,
    ):
        client = TestClient(create_test_app())

        for _ in range(3):
            assert client.get(API_PATH).status_code == 200


def test_user_based_limit(mock_settings, clean_storage):
    """Verify authenticated users get a higher rate limit."""
    mock_settings.rate_limit_per_minute = 1
    mock_settings.rate_limit_authenticated_per_minute = 3

    mock_user = MagicMock()
    mock_user.id = "user-123"

    mock_context = MagicMock(spec=HookContext)
    mock_context.user = mock_user
    mock_context.account_id = "some-account"

    with _patch_settings(mock_settings), patch(
        "snackbase.infrastructure.api.middleware.rate_limit_middleware.get_current_context",
        return_value=mock_context,
    ):
        client = TestClient(create_test_app())

        for _ in range(3):
            response = client.get(API_PATH)
            assert response.status_code == 200
            assert response.headers["X-RateLimit-Limit"] == "3"
            assert response.headers["X-RateLimit-Burst"] == "3"

        assert client.get(API_PATH).status_code == 429


def test_rate_limit_disabled(mock_settings, clean_storage):
    """Verify middleware does nothing when disabled."""
    mock_settings.rate_limit_enabled = False
    mock_settings.rate_limit_per_minute = 1

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        for _ in range(5):
            response = client.get(API_PATH)
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers


def test_endpoint_override(mock_settings, clean_storage):
    """Verify endpoint-specific overrides work."""
    mock_settings.rate_limit_per_minute = 10
    mock_settings.rate_limit_endpoints = {API_PATH: 1}

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        response = client.get(API_PATH)
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "1"

        assert client.get(API_PATH).status_code == 429


def test_static_asset_is_not_metered(mock_settings, clean_storage):
    """SPA assets sit outside the API prefix and must not consume tokens."""
    mock_settings.rate_limit_per_minute = 1

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        for _ in range(200):
            response = client.get("/assets/app.js")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers


def test_health_is_not_metered(mock_settings, clean_storage):
    """Health checks must stay reachable no matter how busy the API bucket is."""
    mock_settings.rate_limit_per_minute = 1

    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        # Exhaust the API bucket first.
        assert client.get(API_PATH).status_code == 200
        assert client.get(API_PATH).status_code == 429

        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers


def test_api_prefix_root_is_metered(mock_settings, clean_storage):
    """The API root endpoint is the prefix itself and is still metered."""
    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        response = client.get("/api/v1")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"


def test_prefix_substring_is_not_metered(mock_settings, clean_storage):
    """`/api/v1x/foo` merely shares a substring — the match needs a segment boundary."""
    with _patch_settings(mock_settings):
        client = TestClient(create_test_app())

        response = client.get("/api/v1x/foo")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
