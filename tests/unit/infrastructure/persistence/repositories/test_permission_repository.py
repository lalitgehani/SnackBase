"""Unit tests for PermissionRepository."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import PermissionModel
from snackbase.infrastructure.persistence.repositories import PermissionRepository


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session):
    """Create a PermissionRepository instance."""
    return PermissionRepository(mock_session)


@pytest.mark.asyncio
async def test_create_permission(repository, mock_session):
    """Test creating a permission."""
    permission = PermissionModel(
        role_id=1,
        collection="test_collection",
        rules=json.dumps({"read": {"rule": "true", "fields": "*"}}),
    )

    result = await repository.create(permission)

    assert result == permission
    mock_session.add.assert_called_once_with(permission)
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id(repository, mock_session):
    """Test getting a permission by ID."""
    permission_id = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = PermissionModel(id=permission_id)
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(permission_id)

    assert result is not None
    assert result.id == permission_id
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_role_id(repository, mock_session):
    """Test getting permissions by role ID."""
    role_id = 1
    permissions = [PermissionModel(role_id=role_id), PermissionModel(role_id=role_id)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = permissions
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_role_id(role_id)

    assert len(result) == 2
    assert result[0].role_id == role_id
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_collection(repository, mock_session):
    """Test getting permissions by collection."""
    collection = "posts"
    permissions = [
        PermissionModel(collection=collection),
        PermissionModel(collection="*"),
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = permissions
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_collection(collection)

    assert len(result) == 2
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_permission(repository, mock_session):
    """Test deleting a permission."""
    permission_id = 1
    permission = PermissionModel(id=permission_id)
    
    # Mock get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = permission
    mock_session.execute.return_value = mock_result

    result = await repository.delete(permission_id)

    assert result is True
    mock_session.delete.assert_called_once_with(permission)
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_delete_non_existent_permission(repository, mock_session):
    """Test deleting a non-existent permission."""
    permission_id = 999
    
    # Mock get_by_id returning None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.delete(permission_id)

    assert result is False
    mock_session.delete.assert_not_called()
