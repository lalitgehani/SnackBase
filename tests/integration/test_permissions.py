"""Integration tests for Permissions API."""

import pytest
from httpx import AsyncClient

from snackbase.infrastructure.auth import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID


@pytest.fixture
def superadmin_headers():
    """Create headers for a superadmin user."""
    token = jwt_service.create_access_token(
        user_id="superadmin-id",
        account_id=SYSTEM_ACCOUNT_ID,
        email="admin@system.com",
        role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_user_headers():
    """Create headers for a regular user."""
    token = jwt_service.create_access_token(
        user_id="user-id",
        account_id="AB1234",
        email="user@example.com",
        role="user",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_permission(client: AsyncClient, superadmin_headers):
    """Test creating a permission as superadmin."""
    payload = {
        "role_id": 1,  # Assuming 'admin' role has ID 1 from seed
        "collection": "posts",
        "rules": {
            "create": {"rule": "true", "fields": "*"},
            "read": {"rule": "true", "fields": "*"},
        },
    }

    response = await client.post(
        "/api/v1/permissions", json=payload, headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["role_id"] == 1
    assert data["collection"] == "posts"
    assert data["rules"]["create"]["rule"] == "true"
    assert data["rules"]["read"]["rule"] == "true"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_permission_forbidden(client: AsyncClient, regular_user_headers):
    """Test that regular users cannot create permissions."""
    payload = {
        "role_id": 1,
        "collection": "posts",
        "rules": {"read": {"rule": "true", "fields": "*"}},
    }

    response = await client.post(
        "/api/v1/permissions", json=payload, headers=regular_user_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_permission_invalid_role(client: AsyncClient, superadmin_headers):
    """Test creating permission for non-existent role."""
    payload = {
        "role_id": 999,
        "collection": "posts",
        "rules": {"read": {"rule": "true", "fields": "*"}},
    }

    response = await client.post(
        "/api/v1/permissions", json=payload, headers=superadmin_headers
    )

    assert response.status_code == 404
    assert "Role with ID 999 not found" in response.json()["message"]


@pytest.mark.asyncio
async def test_list_permissions(client: AsyncClient, superadmin_headers):
    """Test listing permissions."""
    # Create a permission first
    payload = {
        "role_id": 1,
        "collection": "test_collection",
        "rules": {"read": {"rule": "true", "fields": "*"}},
    }
    await client.post("/api/v1/permissions", json=payload, headers=superadmin_headers)

    response = await client.get("/api/v1/permissions", headers=superadmin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_permission_by_id(client: AsyncClient, superadmin_headers):
    """Test getting a permission by ID."""
    # Create a permission
    payload = {
        "role_id": 1,
        "collection": "single_test",
        "rules": {"read": {"rule": "true", "fields": "*"}},
    }
    create_res = await client.post(
        "/api/v1/permissions", json=payload, headers=superadmin_headers
    )
    permission_id = create_res.json()["id"]

    # Get by ID
    response = await client.get(
        f"/api/v1/permissions/{permission_id}", headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == permission_id
    assert data["collection"] == "single_test"


@pytest.mark.asyncio
async def test_delete_permission(client: AsyncClient, superadmin_headers):
    """Test deleting a permission."""
    # Create a permission
    payload = {
        "role_id": 1,
        "collection": "delete_test",
        "rules": {"read": {"rule": "true", "fields": "*"}},
    }
    create_res = await client.post(
        "/api/v1/permissions", json=payload, headers=superadmin_headers
    )
    permission_id = create_res.json()["id"]

    # Delete
    response = await client.delete(
        f"/api/v1/permissions/{permission_id}", headers=superadmin_headers
    )

    assert response.status_code == 204

    # Verify deletion
    get_res = await client.get(
        f"/api/v1/permissions/{permission_id}", headers=superadmin_headers
    )
    assert get_res.status_code == 404
