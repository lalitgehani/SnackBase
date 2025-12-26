"""Unit tests for roles router matrix format endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.persistence.database import get_db_session


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_get_permissions_matrix_success(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    client,
):
    """Test successful matrix retrieval."""
    # Setup mocks
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_mock.name = "editor"
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    # Mock collections
    coll_repo = mock_coll_repo.return_value
    coll1 = MagicMock()
    coll1.name = "customers"
    coll2 = MagicMock()
    coll2.name = "orders"
    coll_repo.get_all = AsyncMock(return_value=([coll1, coll2], 2))

    # Mock permissions (only for customers)
    perm_repo = mock_perm_repo.return_value
    perm_mock = MagicMock()
    perm_mock.id = 1
    perm_mock.collection = "customers"
    perm_mock.rules = '{"create": {"rule": "true", "fields": "*"}}'
    perm_repo.get_by_role_id = AsyncMock(return_value=[perm_mock])

    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    response = client.get("/api/v1/roles/1/permissions/matrix")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["role_id"] == 1
    assert data["role_name"] == "editor"
    assert len(data["permissions"]) == 2  # Both collections

    # Verify customers has permission
    customers_perm = next(p for p in data["permissions"] if p["collection"] == "customers")
    assert customers_perm["create"] is not None

    # Verify orders has no permissions
    orders_perm = next(p for p in data["permissions"] if p["collection"] == "orders")
    assert orders_perm["create"] is None

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_get_permissions_matrix_invalid_role(mock_role_repo, client):
    """Test matrix retrieval with non-existent role."""
    role_repo = mock_role_repo.return_value
    role_repo.get_by_id = AsyncMock(return_value=None)

    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    response = client.get("/api/v1/roles/999/permissions/matrix")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_get_permissions_matrix_empty_role(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    client,
):
    """Test matrix for role with no permissions."""
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_mock.name = "viewer"
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    coll_repo = mock_coll_repo.return_value
    coll1 = MagicMock()
    coll1.name = "customers"
    coll_repo.get_all = AsyncMock(return_value=([coll1], 1))

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])  # No permissions

    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    response = client.get("/api/v1/roles/1/permissions/matrix")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["permissions"]) == 1
    assert data["permissions"][0]["create"] is None

    # Cleanup
    app.dependency_overrides = {}


def test_get_permissions_matrix_non_superadmin(client):
    """Test matrix endpoint requires superadmin access."""
    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock non-superadmin user
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_non_superadmin():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Superadmin access required")

    app.dependency_overrides[require_superadmin] = mock_non_superadmin

    response = client.get("/api/v1/roles/1/permissions/matrix")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_get_permissions_matrix_format(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    client,
):
    """Test matrix response structure is correct."""
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_mock.name = "editor"
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    coll_repo = mock_coll_repo.return_value
    coll1 = MagicMock()
    coll1.name = "customers"
    coll_repo.get_all = AsyncMock(return_value=([coll1], 1))

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])

    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    response = client.get("/api/v1/roles/1/permissions/matrix")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify structure
    assert "role_id" in data
    assert "role_name" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)

    # Verify permission structure
    perm = data["permissions"][0]
    assert "collection" in perm
    assert "permission_id" in perm
    assert "create" in perm
    assert "read" in perm
    assert "update" in perm
    assert "delete" in perm

    # Cleanup
    app.dependency_overrides = {}
