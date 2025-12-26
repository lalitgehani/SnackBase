"""Unit tests for collections router names endpoint."""

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


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
def test_get_collection_names_success(mock_coll_repo, client):
    """Test successful collection names retrieval."""
    # Mock collections
    coll1 = MagicMock()
    coll1.name = "customers"
    coll2 = MagicMock()
    coll2.name = "orders"
    coll3 = MagicMock()
    coll3.name = "products"

    # Setup repository mock
    coll_repo = MagicMock()
    coll_repo.list_all = AsyncMock(return_value=[coll1, coll2, coll3])
    mock_coll_repo.return_value = coll_repo

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

    response = client.get("/api/v1/collections/names")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "names" in data
    assert "total" in data
    assert data["total"] == 3
    assert "customers" in data["names"]
    assert "orders" in data["names"]
    assert "products" in data["names"]

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
def test_get_collection_names_empty(mock_coll_repo, client):
    """Test collection names when no collections exist."""
    # Setup repository mock
    coll_repo = MagicMock()
    coll_repo.list_all = AsyncMock(return_value=[])
    mock_coll_repo.return_value = coll_repo

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

    response = client.get("/api/v1/collections/names")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["names"] == []
    assert data["total"] == 0

    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
def test_get_collection_names_format(mock_coll_repo, client):
    """Test collection names response structure."""
    # Mock collection
    coll1 = MagicMock()
    coll1.name = "customers"

    # Setup repository mock
    coll_repo = MagicMock()
    coll_repo.list_all = AsyncMock(return_value=[coll1])
    mock_coll_repo.return_value = coll_repo

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

    response = client.get("/api/v1/collections/names")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify structure
    assert isinstance(data, dict)
    assert "names" in data
    assert "total" in data
    assert isinstance(data["names"], list)
    assert isinstance(data["total"], int)

    # Cleanup
    app.dependency_overrides = {}


def test_get_collection_names_non_superadmin(client):
    """Test collection names endpoint requires superadmin access."""
    # Override DB session
    session_mock = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session_mock

    # Mock non-superadmin user
    from snackbase.infrastructure.api.dependencies import require_superadmin

    async def mock_non_superadmin():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Superadmin access required")

    app.dependency_overrides[require_superadmin] = mock_non_superadmin

    response = client.get("/api/v1/collections/names")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Cleanup
    app.dependency_overrides = {}
