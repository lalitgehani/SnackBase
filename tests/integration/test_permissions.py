"""Integration tests for Permissions API."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.infrastructure.persistence.models.user import UserModel
from snackbase.infrastructure.persistence.models.account import AccountModel

from snackbase.infrastructure.auth import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID


@pytest.fixture
async def superadmin_headers(db_session: AsyncSession):
    """Create headers for a superadmin user."""
    from snackbase.infrastructure.persistence.models.role import RoleModel
    
    # Ensure roles exist
    admin_role = RoleModel(id=1, name="admin")
    await db_session.merge(admin_role)
    
    # Ensure system account exists
    account = AccountModel(id=SYSTEM_ACCOUNT_ID, name="System", account_code="SY0000", slug="system")
    await db_session.merge(account)
    
    # Ensure superadmin user exists
    user = UserModel(
        id="superadmin-id", 
        email="admin@system.com", 
        account_id=SYSTEM_ACCOUNT_ID, 
        role_id=1, 
        is_active=True,
        password_hash="fake-hash"
    )
    await db_session.merge(user)
    await db_session.commit()

    token = jwt_service.create_access_token(
        user_id="superadmin-id",
        account_id=SYSTEM_ACCOUNT_ID,
        email="admin@system.com",
        role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def regular_user_headers(db_session: AsyncSession):
    """Create headers for a regular user."""
    from snackbase.infrastructure.persistence.models.role import RoleModel
    
    # Ensure roles exist
    user_role = RoleModel(id=2, name="user")
    await db_session.merge(user_role)
    
    # Ensure account exists
    account = AccountModel(id="AB1234", name="User Account", account_code="AB1234", slug="user-account")
    await db_session.merge(account)
    
    # Ensure regular user exists
    user = UserModel(
        id="user-id", 
        email="user@example.com", 
        account_id="AB1234", 
        role_id=2, 
        is_active=True,
        password_hash="fake-hash"
    )
    await db_session.merge(user)
    await db_session.commit()

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
