"""Integration tests for field-level access control."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    AccountRepository,
    UserRepository,
    RoleRepository,
)
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    UserModel,
)


@pytest_asyncio.fixture(autouse=True)
async def test_account_and_users(db_session: AsyncSession):
    """Create test account and users."""
    # Create account
    account_repo = AccountRepository(db_session)
    account = AccountModel(
        id="TE1234",  # Format: 2 letters + 4 digits
        account_code="TE1234",
        slug="testaccount",
        name="Test Account",
    )
    await account_repo.create(account)

    # Get or create system account (migration may have already created it)
    from sqlalchemy import select
    result = await db_session.execute(
        select(AccountModel).where(AccountModel.account_code == "SY0000")
    )
    system_account = result.scalar_one_or_none()
    
    if system_account is None:
        # Create system account if it doesn't exist
        system_account = AccountModel(
            id=SYSTEM_ACCOUNT_ID,
            account_code="SY0000",
            slug="system",
            name="System Account",
        )
        await account_repo.create(system_account)

    
    # Get roles (seeded in conftest)
    from snackbase.infrastructure.persistence.models import RoleModel
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result.scalar_one()
    
    # Create superadmin user (in system account)
    user_repo = UserRepository(db_session)
    superadmin = UserModel(
        id="superadmin-id",
        account_id=SYSTEM_ACCOUNT_ID,
        email="admin@system.com",
        password_hash="hashed",
        role_id=admin_role.id,
        is_active=True,
    )
    await user_repo.create(superadmin)
    
    # Create limited user (in test account)
    limited_user = UserModel(
        id="limited-user-id",
        account_id=account.id,
        email="limited@example.com",
        password_hash="hashed",
        role_id=user_role.id,
        is_active=True,
    )
    await user_repo.create(limited_user)
    
    # Create account admin (in test account)
    account_admin = UserModel(
        id="account-admin-id",
        account_id=account.id,
        email="accadmin@example.com",
        password_hash="hashed",
        role_id=admin_role.id,
        is_active=True,
    )
    await user_repo.create(account_admin)
    
    await db_session.commit()
    
    return {
        "account": account,
        "superadmin": superadmin,
        "limited_user": limited_user,
        "account_admin": account_admin,
        "admin_role": admin_role,
        "user_role": user_role,
    }

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
def limited_user_headers():
    """Create headers for a user with limited field access."""
    token = jwt_service.create_access_token(
        user_id="limited-user-id",
        account_id="TE1234",  # Match the account created in fixture
        email="limited@example.com",
        role="user",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def account_admin_headers():
    """Create headers for an admin user in the test account."""
    token = jwt_service.create_access_token(
        user_id="account-admin-id",
        account_id="TE1234",
        email="accadmin@example.com",
        role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_collection(client: AsyncClient, superadmin_headers, db_session: AsyncSession):
    """Create a test collection with multiple fields."""
    import uuid
    collection_name = f"employees_{uuid.uuid4().hex[:8]}"
    
    collection_data = {
        "name": collection_name,
        "schema": [
            {"name": "name", "type": "text", "required": True},
            {"name": "email", "type": "email", "required": True},
            {"name": "salary", "type": "number", "required": False},
            {"name": "department", "type": "text", "required": False},
        ],
    }
    
    response = await client.post(
        "/api/v1/collections",
        json=collection_data,
        headers=superadmin_headers,
    )
    assert response.status_code == 201
    result = response.json()
    result["name"] = collection_name  # Ensure name is in result
    return result


@pytest_asyncio.fixture
async def limited_permission(
    client: AsyncClient,
    superadmin_headers,
    test_collection,
    db_session: AsyncSession,
):
    """Create permission with limited field access for user role."""
    # Get user role ID (should be 2 from seed)
    permission_data = {
        "role_id": 2,  # user role
        "collection": test_collection["name"],  # Use dynamic collection name
        "rules": {
            "create": {
                "rule": "true",
                "fields": ["name", "email", "department"],  # No salary
            },
            "read": {
                "rule": "true",
                "fields": ["name", "email", "department"],  # No salary
            },
            "update": {
                "rule": "true",
                "fields": ["name", "department"],  # No email or salary
            },
        },
    }
    
    response = await client.post(
        "/api/v1/permissions",
        json=permission_data,
        headers=superadmin_headers,
    )
    assert response.status_code == 201
    return response.json()

    return response.json()


@pytest_asyncio.fixture
async def admin_full_access(client: AsyncClient, superadmin_headers, test_collection):
    """Grant full access to admin role for test collection."""
    permission_data = {
        "role_id": 1,  # admin role
        "collection": test_collection["name"],
        "rules": {
            "create": {"rule": "true", "fields": "*"},
            "read": {"rule": "true", "fields": "*"},
            "update": {"rule": "true", "fields": "*"},
            "delete": {"rule": "true", "fields": "*"},
        },
    }
    await client.post(
        "/api/v1/permissions",
        json=permission_data,
        headers=superadmin_headers,
    )
    return permission_data
@pytest.mark.asyncio
async def test_create_with_allowed_fields(
    client: AsyncClient,
    limited_user_headers,
    test_collection,
    limited_permission,
):
    """Test that create succeeds with allowed fields."""
    record_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering",
    }
    
    response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert data["department"] == "Engineering"


@pytest.mark.asyncio
async def test_create_with_unauthorized_field(
    client: AsyncClient,
    limited_user_headers,
    test_collection,
    limited_permission,
):
    """Test that create fails with 422 for unauthorized field."""
    record_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "salary": 75000,  # Not allowed
    }
    
    response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "salary" in error_detail["unauthorized_fields"]
    assert error_detail["field_type"] == "restricted"


@pytest.mark.asyncio
async def test_create_with_system_field(
    client: AsyncClient,
    limited_user_headers,
    test_collection,
    limited_permission,
):
    """Test that create fails with 422 when trying to set system field."""
    record_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "id": "custom-id",  # System field - not allowed
    }
    
    response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "id" in error_detail["unauthorized_fields"]
    assert error_detail["field_type"] == "system"


@pytest.mark.asyncio
async def test_read_filters_response_fields(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
):
    """Test that restricted fields are filtered from response."""
    # Create record as account admin
    record_data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "salary": 85000,
        "department": "Marketing",
    }
    
    create_response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=account_admin_headers,
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]
    
    # Read as limited user
    response = await client.get(
        f"/api/v1/records/{test_collection['name']}/{record_id}",
        headers=limited_user_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have allowed fields
    assert "name" in data
    assert "email" in data
    assert "department" in data
    
    # Should have system fields
    assert "id" in data
    assert "created_at" in data
    
    # Should NOT have restricted field
    assert "salary" not in data


@pytest.mark.asyncio
async def test_read_wildcard_returns_all_fields(
    client: AsyncClient,
    account_admin_headers,
    superadmin_headers,
    test_collection,
):
    """Test that explicit wildcard returns all fields."""
    # Create permission with wildcard
    permission_data = {
        "role_id": 1,  # admin role
        "collection": test_collection["name"],
        "rules": {
            "create": {"rule": "true", "fields": "*"},
            "read": {"rule": "true", "fields": "*"},
        },
    }
    
    await client.post(
        "/api/v1/permissions",
        json=permission_data,
        headers=superadmin_headers,
    )
    
    # Create record as account admin
    record_data = {
        "name": "Admin User",
        "email": "admin@example.com",
        "salary": 100000,
        "department": "Executive",
    }
    
    create_response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=account_admin_headers,
    )
    record_id = create_response.json()["id"]
    
    # Read record
    response = await client.get(
        f"/api/v1/records/{test_collection['name']}/{record_id}",
        headers=account_admin_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have all fields
    assert data["name"] == "Admin User"
    assert data["email"] == "admin@example.com"
    assert data["salary"] == 100000
    assert data["department"] == "Executive"


@pytest.mark.asyncio
async def test_update_with_allowed_fields(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
):
    """Test that update succeeds with allowed fields."""
    # Create record as account admin
    record_data = {
        "name": "Original Name",
        "email": "test@example.com",
        "department": "Sales",
    }
    
    create_response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=account_admin_headers,
    )
    record_id = create_response.json()["id"]
    
    # Update as limited user (can update name and department)
    update_data = {
        "name": "Updated Name",
        "department": "Marketing",
    }
    
    response = await client.patch(
        f"/api/v1/records/{test_collection['name']}/{record_id}",
        json=update_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["department"] == "Marketing"


@pytest.mark.asyncio
async def test_update_with_unauthorized_field(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
):
    """Test that update fails with 422 for unauthorized field."""
    # Create record as account admin
    record_data = {
        "name": "Test User",
        "email": "test@example.com",
        "salary": 60000,
    }
    
    create_response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=account_admin_headers,
    )
    record_id = create_response.json()["id"]
    
    # Try to update salary (not allowed for limited user)
    update_data = {
        "salary": 70000,
    }
    
    response = await client.patch(
        f"/api/v1/records/{test_collection['name']}/{record_id}",
        json=update_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "salary" in error_detail["unauthorized_fields"]


@pytest.mark.asyncio
async def test_update_with_system_field(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
):
    """Test that update fails with 422 when trying to update system field."""
    # Create record
    record_data = {
        "name": "Test User",
        "email": "test@example.com",
    }
    
    create_response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
        json=record_data,
        headers=account_admin_headers,
    )
    record_id = create_response.json()["id"]
    
    # Try to update created_at (system field)
    update_data = {
        "name": "Updated Name",
        "created_at": "2020-01-01T00:00:00Z",
    }
    
    response = await client.patch(
        f"/api/v1/records/{test_collection['name']}/{record_id}",
        json=update_data,
        headers=limited_user_headers,
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "created_at" in error_detail["unauthorized_fields"]
    assert error_detail["field_type"] == "system"


@pytest.mark.asyncio
async def test_list_filters_response_fields(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
):
    """Test that list endpoint filters restricted fields."""
    # Create multiple records as account admin
    records_data = [
        {"name": "User 1", "email": "user1@example.com", "salary": 50000, "department": "IT"},
        {"name": "User 2", "email": "user2@example.com", "salary": 60000, "department": "HR"},
    ]
    
    for record_data in records_data:
        response = await client.post(
        f"/api/v1/records/{test_collection['name']}",
            json=record_data,
            headers=account_admin_headers,
        )
        assert response.status_code == 201
    
    # List as limited user
    response = await client.get(
        f"/api/v1/records/{test_collection['name']}",
        headers=limited_user_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    
    # Check that all records have filtered fields
    for item in data["items"]:
        # Should have allowed fields
        assert "name" in item
        assert "email" in item
        assert "department" in item
        
        # Should have system fields
        assert "id" in item
        
        # Should NOT have restricted field
        assert "salary" not in item


@pytest.mark.asyncio
async def test_pii_masking_after_field_filtering(
    client: AsyncClient,
    account_admin_headers,
    limited_user_headers,
    test_collection,
    limited_permission,
    admin_full_access,
    superadmin_headers,
):
    """Test that PII masking is applied after field filtering."""
    # Create collection with PII field (use unique name to avoid conflict with users router)
    import uuid
    collection_name = f"test_users_{uuid.uuid4().hex[:8]}"
    collection_data = {
        "name": collection_name,
        "schema": [
            {"name": "name", "type": "text", "required": True},
            {"name": "email", "type": "email", "required": True, "pii": True, "mask_type": "email"},
            {"name": "phone", "type": "text", "required": False, "pii": True, "mask_type": "phone"},
            {"name": "department", "type": "text", "required": False},
        ],
    }

    response = await client.post(
        "/api/v1/collections",
        json=collection_data,
        headers=superadmin_headers,
    )
    assert response.status_code == 201

    # Create permission with limited fields (including PII field)
    permission_data = {
        "role_id": 2,  # user role
        "collection": collection_name,
        "rules": {
            "read": {
                "rule": "true",
                "fields": ["name", "email"],  # email is PII
            },
        },
    }

    await client.post(
        "/api/v1/permissions",
        json=permission_data,
        headers=superadmin_headers,
    )

    # Grant admin access to the test collection
    admin_permission = {
        "role_id": 1,  # admin role
        "collection": collection_name,
        "rules": {
            "create": {"rule": "true", "fields": "*"},
            "read": {"rule": "true", "fields": "*"},
        },
    }
    await client.post(
        "/api/v1/permissions",
        json=admin_permission,
        headers=superadmin_headers,
    )
    # Create record with PII data
    record_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-123-4567",
        "department": "Engineering",
    }

    create_response = await client.post(
        f"/api/v1/records/{collection_name}",
        json=record_data,
        headers=account_admin_headers,
    )
    record_id = create_response.json()["id"]

    # Read as limited user (no pii_access group)
    response = await client.get(
        f"/api/v1/records/{collection_name}/{record_id}",
        headers=limited_user_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have allowed fields
    assert "name" in data
    assert "email" in data
    
    # Email should be masked (PII masking applied)
    assert data["email"] != "john.doe@example.com"
    assert "*" in data["email"] or data["email"].startswith("j")
    
    # Should NOT have phone (not in allowed fields)
    assert "phone" not in data
    
    # Should NOT have department (not in allowed fields)
    assert "department" not in data
