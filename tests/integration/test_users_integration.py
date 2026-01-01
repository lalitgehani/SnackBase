"""Integration tests for Users API."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test creating a new user."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # First, create an account for the user
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1234", name="Test Account", slug="test-account")
    db_session.add(account)
    await db_session.commit()

    # Get role
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "testuser@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
        "is_active": True,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["account_id"] == account_id
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_oauth_user(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test creating a new OAuth user."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create an account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="OA1234", name="OAuth Account", slug="oauth-account")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create OAuth user
    payload = {
        "email": "oauth@example.com",
        "password": "RandomUnknowablePassword123!",
        "account_id": account_id,
        "role_id": role.id,
        "auth_provider": "oauth",
        "auth_provider_name": "google",
        "external_id": "google-123",
        "external_email": "oauth@gmail.com",
        "profile_data": {"name": "OAuth User"},
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["auth_provider"] == "oauth"
    assert data["auth_provider_name"] == "google"
    assert data["external_id"] == "google-123"
    assert data["external_email"] == "oauth@gmail.com"
    assert data["profile_data"] == {"name": "OAuth User"}


@pytest.mark.asyncio
async def test_create_user_weak_password(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test creating a user with weak password fails."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1235", name="Test Account 2", slug="test-account-2")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Weak password (missing special char)
    payload = {
        "email": "weakpass@example.com",
        "password": "weakpass123",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test creating a user with duplicate email fails."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1236", name="Test Account 3", slug="test-account-3")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    payload = {
        "email": "duplicate@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }

    # First creation should succeed
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201

    # Second creation should fail
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test listing users."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_users_with_filters(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test listing users with filters."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1237", name="Filter Test", slug="filter-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create some users
    for i in range(3):
        payload = {
            "email": f"filter{i}@example.com",
            "password": "TestPass123!@#",
            "account_id": account_id,
            "role_id": role.id,
        }
        await client.post("/api/v1/users", json=payload, headers=headers)

    # Filter by account_id
    response = await client.get(f"/api/v1/users?account_id={account_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 3
    for user in data["items"]:
        assert user["account_id"] == account_id

    # Filter by search
    response = await client.get(f"/api/v1/users?search=filter1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert any(user["email"] == "filter1@example.com" for user in data["items"])


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test pagination of users list."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1238", name="Pagination Test", slug="pagination-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create some users
    for i in range(5):
        payload = {
            "email": f"page{i}@example.com",
            "password": "TestPass123!@#",
            "account_id": account_id,
            "role_id": role.id,
        }
        await client.post("/api/v1/users", json=payload, headers=headers)

    # Get first page
    response = await client.get("/api/v1/users?skip=0&limit=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test getting a user by ID."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1239", name="Get Test", slug="get-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "getbyid@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Get user by ID
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "getbyid@example.com"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test updating a user."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1240", name="Update Test", slug="update-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "updateuser@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Update user
    update_payload = {"email": "updated@example.com"}
    response = await client.patch(f"/api/v1/users/{user_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "updated@example.com"


@pytest.mark.asyncio
async def test_update_user_deactivate(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test deactivating a user via update."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1241", name="Deactivate Test", slug="deactivate-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "deactivate@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Deactivate user
    update_payload = {"is_active": False}
    response = await client.patch(f"/api/v1/users/{user_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_reset_user_password(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test resetting a user's password."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1242", name="Password Test", slug="password-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "password@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Reset password
    reset_payload = {"new_password": "NewPass456!@#"}
    response = await client.put(f"/api/v1/users/{user_id}/password", json=reset_payload, headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reset_user_password_weak_password(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test resetting password with weak password fails."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1243", name="Weak Password Test", slug="weak-password-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "weakreset@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Try to reset with weak password
    reset_payload = {"new_password": "weak"}
    response = await client.put(f"/api/v1/users/{user_id}/password", json=reset_payload, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_deactivate_user(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test deactivating a user (soft delete)."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1244", name="Soft Delete Test", slug="soft-delete-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create user
    payload = {
        "email": "softdelete@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # Deactivate user
    response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 204

    # Verify user is deactivated
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_non_superadmin_access_denied(client: AsyncClient, regular_user_token: str):
    """Test that regular users cannot access users endpoints."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}

    # List users
    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

    # Create user
    payload = {
        "email": "hacker@example.com",
        "password": "TestPass123!@#",
        "account_id": "AB0000",
        "role_id": 1,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 403

    # Update user
    response = await client.patch("/api/v1/users/some-id", json={"email": "new@example.com"}, headers=headers)
    assert response.status_code == 403

    # Delete user
    response = await client.delete("/api/v1/users/some-id", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_crud_lifecycle(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test full CRUD lifecycle of a user."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create test account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="AB1245", name="Lifecycle Test", slug="lifecycle-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # 1. Create User
    payload = {
        "email": "lifecycle@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
        "is_active": True,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    user_id = response.json()["id"]
    assert response.json()["email"] == "lifecycle@example.com"

    # 2. Get User
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user_id

    # 3. Update User
    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"email": "lifecycle_updated@example.com"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["email"] == "lifecycle_updated@example.com"

    # 4. Reset Password
    response = await client.put(
        f"/api/v1/users/{user_id}/password",
        json={"new_password": "NewPassword789!@#"},
        headers=headers
    )
    assert response.status_code == 200

    # 5. List Users - verify user appears
    response = await client.get(f"/api/v1/users?account_id={account_id}", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["id"] == user_id for item in items)

    # 6. Deactivate User
    response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 204

    # 7. Verify Deactivation
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False
