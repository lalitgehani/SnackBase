import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_middleware_skips_health_endpoints(client: AsyncClient):
    """Verify that health endpoints are skipped by the authentication middleware."""
    # Health checks should return 200 without any credentials
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    
    response = await client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"

@pytest.mark.asyncio
async def test_middleware_handles_unauthenticated_request(client: AsyncClient):
    """Verify that unauthenticated requests to protected endpoints proceed but have no user."""
    # We hit a protected endpoint without credentials
    # The middleware should let it pass, and the dependency should eventually return 401
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_middleware_handles_invalid_token(client: AsyncClient):
    """Verify that invalid tokens are handled gracefully by the middleware."""
    # Hit endpoint with invalid token format
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": "Bearer invalid-token-format"}
    )
    # Authenticator._authenticate_jwt will raise AuthenticationError
    # Middleware logs it and proceeds. Dependency then returns 401.
    assert response.status_code == 401
