"""Unit tests for GroupRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import GroupModel, UsersGroupsModel
from snackbase.infrastructure.persistence.repositories.group_repository import GroupRepository


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session




@pytest.fixture
def group_repo(mock_session):
    """Create a GroupRepository instance."""
    return GroupRepository(mock_session)


@pytest.mark.asyncio
async def test_create_group(group_repo, mock_session):
    """Test creating a group."""
    group = GroupModel(id="g1", name="Admins", account_id="acc1")
    
    # Mock the execute result for the reload query
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = group
    mock_session.execute.return_value = mock_result
    
    result = await group_repo.create(group)
    
    assert result == group
    mock_session.add.assert_called_once_with(group)
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id(group_repo, mock_session):
    """Test getting a group by ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = GroupModel(id="g1")
    mock_session.execute.return_value = mock_result
    
    result = await group_repo.get_by_id("g1")
    
    assert result is not None
    assert result.id == "g1"
    mock_session.execute.assert_called_once()




@pytest.mark.asyncio
async def test_add_user(group_repo, mock_session):
    """Test adding a user to a group."""
    group_id = "g1"
    user_id = "u1"
    
    await group_repo.add_user(group_id, user_id)
    
    mock_session.add.assert_called_once()
    assert isinstance(mock_session.add.call_args[0][0], UsersGroupsModel)
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_remove_user(group_repo, mock_session):
    """Test removing a user from a group."""
    group_id = "g1"
    user_id = "u1"
    
    await group_repo.remove_user(group_id, user_id)
    
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()
