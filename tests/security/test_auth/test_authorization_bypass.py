import pytest
import pytest_asyncio
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import RoleModel
from tests.security.conftest import AttackClient


@pytest.mark.asyncio
async def test_auth_az_001_access_without_token(attack_client: AttackClient):
    """AUTH-AZ-001: Attempt access without an authorization token."""
    response = await attack_client.get(
        "/api/v1/auth/me",
        headers={},
        description="Accessing protected endpoint without token"
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_auth_az_002_access_with_invalid_token(attack_client: AttackClient):
    """AUTH-AZ-002: Attempt access with an invalid/malformed token."""
    headers = {"Authorization": "Bearer invalid-token-format"}
    response = await attack_client.get(
        "/api/v1/auth/me",
        headers=headers,
        description="Accessing protected endpoint with invalid token"
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_az_003_regular_user_to_superadmin_endpoint(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-003: Verify regular user cannot access superadmin listing of accounts."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await attack_client.get(
        "/api/v1/accounts",
        headers=headers,
        description="Regular user attempting to list accounts (superadmin only)"
    )
    
    # Superadmin endpoints should return 403 Forbidden for regular users
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_az_004_regular_user_to_collections_endpoint(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-004: Verify regular user cannot access collections management."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await attack_client.get(
        "/api/v1/collections",
        headers=headers,
        description="Regular user attempting to list collections (superadmin only)"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_az_005_regular_user_to_roles_endpoint(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-005: Verify regular user cannot access roles management."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await attack_client.get(
        "/api/v1/roles",
        headers=headers,
        description="Regular user attempting to list roles (superadmin only)"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_az_006_regular_user_to_permissions_endpoint(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-006: Verify regular user cannot access permissions management."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await attack_client.get(
        "/api/v1/permissions",
        headers=headers,
        description="Regular user attempting to list permissions (superadmin only)"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_az_007_regular_user_to_dashboard_stats(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-007: Verify regular user cannot access dashboard statistics."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await attack_client.get(
        "/api/v1/dashboard/stats",
        headers=headers,
        description="Regular user attempting to access dashboard stats"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_az_008_superadmin_to_all_endpoints(
    attack_client: AttackClient, 
    superadmin_token: str
):
    """AUTH-AZ-008: Verify superadmin can access all sensitive endpoints."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    endpoints = [
        "/api/v1/accounts",
        "/api/v1/collections",
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/dashboard/stats"
    ]
    
    for endpoint in endpoints:
        response = await attack_client.get(
            endpoint,
            headers=headers,
            description=f"Superadmin accessing {endpoint}"
        )
        assert response.status_code == status.HTTP_200_OK, f"Superadmin should access {endpoint}"


@pytest.mark.asyncio
async def test_auth_az_009_bypass_via_http_method_override(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-009: Attempt to bypass authorization using HTTP method override headers."""
    headers = {
        "Authorization": f"Bearer {regular_user_token}",
        "X-HTTP-Method-Override": "GET"
    }
    
    # We use POST to a restricted GET endpoint with override
    response = await attack_client.post(
        "/api/v1/accounts",
        json={},
        headers=headers,
        description="Method override attempt (X-HTTP-Method-Override: GET)"
    )
    
    # FastAPI/Starlette doesn't support method override by default, 
    # so it should be strictly 405 Method Not Allowed or 403 Forbidden
    assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_auth_az_010_bypass_via_path_traversal(attack_client: AttackClient, regular_user_token: str):
    """AUTH-AZ-010: Attempt to bypass authorization using path traversal."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    
    # Attempting to access /api/v1/accounts via traversal from /api/v1/auth/me
    response = await attack_client.get(
        "/api/v1/auth/../accounts",
        headers=headers,
        description="Path traversal attempt (/api/v1/auth/../accounts)"
    )
    
    # Modern web servers/frameworks normalize paths, so this should still hit /api/v1/accounts 
    # and be denied with 403, or be 404 if not normalized as expected.
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
