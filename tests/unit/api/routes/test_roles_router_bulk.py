"""Unit tests for roles router bulk permissions endpoint."""

import json
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


@patch("snackbase.infrastructure.api.routes.roles_router.get_permission_cache")
@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_bulk_update_permissions_success(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    mock_cache,
    client,
):
    """Test successful bulk permission update."""
    # Setup mocks
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_mock.name = "editor"
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])
    perm_repo.create = AsyncMock()

    coll_repo = mock_coll_repo.return_value
    coll_mock = MagicMock()
    coll_mock.name = "customers"
    coll_repo.get_by_name = AsyncMock(return_value=coll_mock)

    cache_mock = MagicMock()
    cache_mock.invalidate_all = MagicMock()
    mock_cache.return_value = cache_mock

    # Override DB session
    session_mock = AsyncMock()
    session_mock.commit = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        user_mock.account_id = "SY0000"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    payload = {
        "updates": [
            {
                "collection": "customers",
                "operation": "create",
                "rule": "true",
                "fields": "*",
            }
        ]
    }

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 0
    assert len(data["errors"]) == 0

    # Verify cache invalidated
    cache_mock.invalidate_all.assert_called_once()

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_bulk_update_permissions_invalid_role(mock_role_repo, client):
    """Test bulk update fails with non-existent role."""
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
        user_mock.account_id = "SY0000"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    payload = {"updates": [{"collection": "customers", "operation": "create", "rule": "true", "fields": "*"}]}

    response = client.put("/api/v1/roles/999/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.get_permission_cache")
@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_bulk_update_permissions_invalid_collection(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    mock_cache,
    client,
):
    """Test bulk update with invalid collection name."""
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])

    coll_repo = mock_coll_repo.return_value
    coll_repo.get_by_name = AsyncMock(return_value=None)  # Collection not found

    cache_mock = MagicMock()
    mock_cache.return_value = cache_mock

    # Override DB session
    session_mock = AsyncMock()
    session_mock.commit = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    payload = {
        "updates": [
            {"collection": "nonexistent", "operation": "create", "rule": "true", "fields": "*"}
        ]
    }

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success_count"] == 0
    assert data["failure_count"] == 1
    assert "nonexistent" in data["errors"][0]

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.get_permission_cache")
@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_bulk_update_permissions_invalid_rule(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    mock_cache,
    client,
):
    """Test bulk update with malformed rule syntax."""
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])

    coll_repo = mock_coll_repo.return_value
    coll_mock = MagicMock()
    coll_repo.get_by_name = AsyncMock(return_value=coll_mock)

    cache_mock = MagicMock()
    mock_cache.return_value = cache_mock

    # Override DB session
    session_mock = AsyncMock()
    session_mock.commit = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    payload = {
        "updates": [
            {"collection": "customers", "operation": "create", "rule": "user.id ==", "fields": "*"}
        ]
    }

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success_count"] == 0
    assert data["failure_count"] == 1
    assert len(data["errors"]) > 0

    # Cleanup
    app.dependency_overrides = {}


def test_bulk_update_permissions_empty_list(client):
    """Test bulk update with empty updates list."""
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

    payload = {"updates": []}

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Cleanup
    app.dependency_overrides = {}


def test_bulk_update_permissions_non_superadmin(client):
    """Test bulk update requires superadmin access."""
    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock non-superadmin user
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_non_superadmin():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Superadmin access required")

    app.dependency_overrides[require_superadmin] = mock_non_superadmin

    payload = {
        "updates": [
            {"collection": "customers", "operation": "create", "rule": "true", "fields": "*"}
        ]
    }

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.roles_router.get_permission_cache")
@patch("snackbase.infrastructure.api.routes.roles_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.PermissionRepository")
@patch("snackbase.infrastructure.api.routes.roles_router.RoleRepository")
def test_bulk_update_permissions_partial_failure(
    mock_role_repo,
    mock_perm_repo,
    mock_coll_repo,
    mock_cache,
    client,
):
    """Test bulk update with some updates succeeding and some failing."""
    role_repo = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = 1
    role_repo.get_by_id = AsyncMock(return_value=role_mock)

    perm_repo = mock_perm_repo.return_value
    perm_repo.get_by_role_id = AsyncMock(return_value=[])
    perm_repo.create = AsyncMock()

    coll_repo = mock_coll_repo.return_value

    # First collection exists, second doesn't
    async def get_by_name_side_effect(name):
        if name == "customers":
            coll_mock = MagicMock()
            coll_mock.name = "customers"
            return coll_mock
        return None

    coll_repo.get_by_name = AsyncMock(side_effect=get_by_name_side_effect)

    cache_mock = MagicMock()
    mock_cache.return_value = cache_mock

    # Override DB session
    session_mock = AsyncMock()
    session_mock.commit = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock superadmin dependency
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_superadmin():
        user_mock = MagicMock()
        user_mock.user_id = "superadmin-id"
        return user_mock

    app.dependency_overrides[require_superadmin] = mock_superadmin

    payload = {
        "updates": [
            {"collection": "customers", "operation": "create", "rule": "true", "fields": "*"},
            {"collection": "nonexistent", "operation": "read", "rule": "true", "fields": "*"},
        ]
    }

    response = client.put("/api/v1/roles/1/permissions/bulk", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 1
    assert len(data["errors"]) == 1

    # Cleanup
    app.dependency_overrides = {}
