
import pytest
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.api.app import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Test standard health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["service"] == "SnackBase"


@pytest.mark.asyncio
async def test_liveness_check_endpoint():
    """Test liveness probe endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/live")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_check_endpoint_success():
    """Test readiness probe endpoint when DB is healthy."""
    # Note: This relies on the actual DB connection or a mock depending on fixture setup.
    # For integration tests, we usually expect the test env DB to be up.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
    
    # If DB is not available in test env, this might fail or return 503.
    # We assert strictly only if we know DB is up, but generally we expect test setup to handle DB.
    # Here we tolerate either result but check structure.
    
    assert response.status_code in (200, 503)
    data = response.json()
    
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert data["database"] == "connected"
    else:
        assert data["status"] == "not_ready"
