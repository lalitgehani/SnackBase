"""Unit tests for Macro API Router."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import get_current_user, require_superadmin
from snackbase.infrastructure.persistence.models.macro import MacroModel


@pytest.fixture
def mock_repo():
    """Mock MacroRepository."""
    with patch(
        "snackbase.infrastructure.api.routes.macros_router.MacroRepository"
    ) as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest_asyncio.fixture
async def async_client():
    """Create a custom AsyncClient for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear dependency overrides after each test."""
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_macro_superadmin(async_client, mock_repo):
    """Test creating a macro as superadmin."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    mock_repo.create.return_value = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT 1",
        parameters='["p1"]',
        created_by="admin",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "name": "test_macro",
        "sql_query": "SELECT 1",
        "parameters": ["p1"],
        "description": "Test",
    }

    # Add dummy header to satisfy get_current_user checks if override fails
    response = await async_client.post(
        "/api/v1/macros/",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "test_macro"


@pytest.mark.asyncio
async def test_create_macro_invalid_query(async_client):
    """Test creating a macro with invalid query (not a SELECT)."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    payload = {
        "name": "test_macro",
        "sql_query": "DELETE FROM users",
    }

    response = await async_client.post(
        "/api/v1/macros/",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_list_macros(async_client, mock_repo):
    """Test listing macros (accessible to all)."""
    async def user_override():
        user = AsyncMock()
        user.user_id = "user"
        return user
    
    app.dependency_overrides[get_current_user] = user_override

    mock_repo.list_all.return_value = [
        MacroModel(id=1, name="m1", sql_query="SELECT 1", parameters="[]", created_at=datetime.now(), updated_at=datetime.now()),
        MacroModel(id=2, name="m2", sql_query="SELECT 2", parameters="[]", created_at=datetime.now(), updated_at=datetime.now()),
    ]

    response = await async_client.get("/api/v1/macros/", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_macro(async_client, mock_repo):
    """Test getting a macro by ID."""
    async def user_override():
        user = AsyncMock()
        return user
    
    app.dependency_overrides[get_current_user] = user_override

    mock_repo.get_by_id.return_value = MacroModel(
        id=1, name="m1", sql_query="SELECT 1", parameters="[]", created_at=datetime.now(), updated_at=datetime.now()
    )

    # Debug: verify mock setup
    print(f"Mock repo get_by_id setup: {mock_repo.get_by_id.return_value}")

    response = await async_client.get("/api/v1/macros/1", headers={"Authorization": "Bearer dummy"})

    if response.status_code != 200:
        print(f"FAILED response: {response.text}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "m1"


@pytest.mark.asyncio
async def test_get_macro_not_found(async_client, mock_repo):
    """Test getting a non-existent macro."""
    async def user_override():
        user = AsyncMock()
        return user
    
    app.dependency_overrides[get_current_user] = user_override

    mock_repo.get_by_id.return_value = None

    response = await async_client.get("/api/v1/macros/999", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_macro_superadmin(async_client, mock_repo):
    """Test updating a macro as superadmin."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    mock_repo.update.return_value = MacroModel(
        id=1, name="updated", sql_query="SELECT 2", parameters="[]", created_at=datetime.now(), updated_at=datetime.now()
    )

    payload = {"name": "updated", "sql_query": "SELECT 2"}

    response = await async_client.put(
        "/api/v1/macros/1",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "updated"


@pytest.mark.asyncio
async def test_delete_macro_superadmin(async_client, mock_repo):
    """Test deleting a macro as superadmin."""
    from snackbase.infrastructure.persistence.repositories.permission_repository import PermissionRepository
    
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    # Mock macro
    mock_macro = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT 1",
        parameters="[]",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_repo.get_by_id.return_value = mock_macro
    mock_repo.delete.return_value = True
    
    # Mock PermissionRepository to prevent it from running real logic
    with patch(
        "snackbase.infrastructure.api.routes.macros_router.PermissionRepository"
    ) as mock_perm_repo_class:
        mock_perm_repo = AsyncMock()
        mock_perm_repo_class.return_value = mock_perm_repo
        mock_perm_repo.find_permissions_using_macro.return_value = []
        
        response = await async_client.delete("/api/v1/macros/1", headers={"Authorization": "Bearer dummy"})
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_macro_not_found(async_client, mock_repo):
    """Test deleting a non-existent macro."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    mock_repo.get_by_id.return_value = None

    response = await async_client.delete("/api/v1/macros/999", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_test_macro_success(async_client, mock_repo):
    """Test successful macro execution."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    # Mock macro with one parameter
    mock_macro = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT :value",
        parameters='["value"]',
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_repo.get_by_id.return_value = mock_macro
    
    payload = {"parameters": ["test_value"]}
    
    response = await async_client.post(
        "/api/v1/macros/1/test",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "result" in data
    assert "execution_time" in data
    assert "rows_affected" in data
    assert data["rows_affected"] == 0


@pytest.mark.asyncio
async def test_test_macro_invalid_param_count(async_client, mock_repo):
    """Test macro test with wrong parameter count."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    # Mock macro with one parameter
    mock_macro = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT :value",
        parameters='["value"]',
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_repo.get_by_id.return_value = mock_macro
    
    # Send wrong number of parameters
    payload = {"parameters": ["val1", "val2"]}
    
    response = await async_client.post(
        "/api/v1/macros/1/test",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_test_macro_not_found(async_client, mock_repo):
    """Test testing a non-existent macro."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    mock_repo.get_by_id.return_value = None
    
    payload = {"parameters": []}
    
    response = await async_client.post(
        "/api/v1/macros/999/test",
        json=payload,
        headers={"Authorization": "Bearer dummy"},
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_macro_in_use(async_client, mock_repo):
    """Test deleting a macro that is used in permissions."""
    from snackbase.infrastructure.persistence.models.permission import PermissionModel
    
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    # Mock macro
    mock_macro = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT 1",
        parameters="[]",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_repo.get_by_id.return_value = mock_macro
    
    # Mock permission repository to return permissions using the macro
    with patch(
        "snackbase.infrastructure.api.routes.macros_router.PermissionRepository"
    ) as mock_perm_repo_class:
        mock_perm_repo = AsyncMock()
        mock_perm_repo_class.return_value = mock_perm_repo
        
        # Return a permission that uses the macro
        mock_permission = PermissionModel(
            id=1,
            role_id=1,
            collection="test",
            rules='{"read": {"rule": "@test_macro()", "fields": "*"}}',
        )
        mock_perm_repo.find_permissions_using_macro.return_value = [mock_permission]
        
        response = await async_client.delete(
            "/api/v1/macros/1",
            headers={"Authorization": "Bearer dummy"},
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "used in" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_macro_unused(async_client, mock_repo):
    """Test deleting a macro that is not used in permissions."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        return user
    
    app.dependency_overrides[require_superadmin] = admin_override
    
    # Mock macro
    mock_macro = MacroModel(
        id=1,
        name="test_macro",
        sql_query="SELECT 1",
        parameters="[]",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_repo.get_by_id.return_value = mock_macro
    mock_repo.delete.return_value = True
    
    # Mock permission repository to return no permissions using the macro
    with patch(
        "snackbase.infrastructure.api.routes.macros_router.PermissionRepository"
    ) as mock_perm_repo_class:
        mock_perm_repo = AsyncMock()
        mock_perm_repo_class.return_value = mock_perm_repo
        mock_perm_repo.find_permissions_using_macro.return_value = []
        
        response = await async_client.delete(
            "/api/v1/macros/1",
            headers={"Authorization": "Bearer dummy"},
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
