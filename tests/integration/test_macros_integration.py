"""Integration tests for Macro Management API (F2.7)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import require_superadmin
from snackbase.infrastructure.persistence.models.macro import MacroModel
from snackbase.infrastructure.persistence.models.permission import PermissionModel
from snackbase.infrastructure.persistence.models.role import RoleModel
from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)
from snackbase.infrastructure.persistence.repositories.permission_repository import (
    PermissionRepository,
)
from unittest.mock import AsyncMock


@pytest.fixture(autouse=True)
def superadmin_override():
    """Override superadmin dependency for all tests."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin_user"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    yield
    # Cleanup is handled by conftest clear_overrides


@pytest.mark.asyncio
async def test_macro_lifecycle(client, db_session: AsyncSession):
    """Test full macro lifecycle: create, test, use in permission, delete."""
    macro_repo = MacroRepository(db_session)
    
    # 1. Create a macro
    create_payload = {
        "name": "test_lifecycle_macro",
        "description": "Test macro for lifecycle",
        "sql_query": "SELECT :user_id",
        "parameters": ["user_id"],
    }
    
    response = await client.post(
        "/api/v1/macros",
        json=create_payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 201
    macro_data = response.json()
    macro_id = macro_data["id"]
    assert macro_data["name"] == "test_lifecycle_macro"
    
    # 2. Test the macro
    test_payload = {"parameters": ["user_123"]}
    
    response = await client.post(
        f"/api/v1/macros/{macro_id}/test",
        json=test_payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 200
    test_result = response.json()
    assert "result" in test_result
    assert "execution_time" in test_result
    assert test_result["rows_affected"] == 0
    
    # 3. Create a permission using the macro
    perm_repo = PermissionRepository(db_session)
    
    # Get the admin role (seeded in conftest)
    from snackbase.infrastructure.persistence.repositories.role_repository import RoleRepository
    role_repo = RoleRepository(db_session)
    admin_role = await role_repo.get_by_name("admin")
    
    # Create permission using the macro
    permission = PermissionModel(
        role_id=admin_role.id,
        collection="test_collection",
        rules='{"read": {"rule": "@test_lifecycle_macro(user.id)", "fields": "*"}}',
    )
    await perm_repo.create(permission)
    await db_session.commit()
    
    # 4. Try to delete the macro (should fail - in use)
    response = await client.delete(
        f"/api/v1/macros/{macro_id}",
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 409
    assert "used in" in response.json()["detail"].lower()
    
    # 5. Delete the permission
    await perm_repo.delete(permission.id)
    await db_session.commit()
    
    # 6. Delete the macro (should succeed now)
    response = await client.delete(
        f"/api/v1/macros/{macro_id}",
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 204
    
    # 7. Verify macro is deleted
    deleted_macro = await macro_repo.get_by_id(macro_id)
    assert deleted_macro is None


@pytest.mark.asyncio
async def test_macro_test_with_invalid_params(client, db_session: AsyncSession):
    """Test macro testing with invalid parameter count."""
    macro_repo = MacroRepository(db_session)
    
    # Create a macro with 2 parameters
    macro = await macro_repo.create(
        name="two_param_macro",
        sql_query="SELECT :p1 + :p2",
        parameters=["p1", "p2"],
        description="Two parameter macro",
        created_by="admin",
    )
    await db_session.commit()
    
    # Test with wrong number of parameters (1 instead of 2)
    test_payload = {"parameters": ["value1"]}
    
    response = await client.post(
        f"/api/v1/macros/{macro.id}/test",
        json=test_payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 422
    assert "Expected 2 parameters" in response.json()["detail"]
    
    # Cleanup
    await macro_repo.delete(macro.id)
    await db_session.commit()


@pytest.mark.asyncio
async def test_duplicate_macro_name(client, db_session: AsyncSession):
    """Test creating a macro with duplicate name."""
    macro_repo = MacroRepository(db_session)
    
    # Create first macro
    macro1 = await macro_repo.create(
        name="duplicate_test",
        sql_query="SELECT 1",
        parameters=[],
        created_by="admin",
    )
    await db_session.commit()
    
    # Try to create second macro with same name
    create_payload = {
        "name": "duplicate_test",
        "sql_query": "SELECT 2",
        "parameters": [],
    }
    
    response = await client.post(
        "/api/v1/macros",
        json=create_payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    # Cleanup handled by conftest rollback


@pytest.mark.asyncio
async def test_update_macro_to_duplicate_name(client, db_session: AsyncSession):
    """Test updating a macro to a name that already exists."""
    macro_repo = MacroRepository(db_session)
    
    # Create two macros
    macro1 = await macro_repo.create(
        name="macro_one",
        sql_query="SELECT 1",
        parameters=[],
        created_by="admin",
    )
    macro2 = await macro_repo.create(
        name="macro_two",
        sql_query="SELECT 2",
        parameters=[],
        created_by="admin",
    )
    await db_session.commit()
    
    # Try to update macro2 to have the same name as macro1
    update_payload = {"name": "macro_one"}
    
    response = await client.put(
        f"/api/v1/macros/{macro2.id}",
        json=update_payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    # Cleanup handled by conftest rollback
