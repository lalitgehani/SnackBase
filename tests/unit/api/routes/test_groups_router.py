"""Unit tests for GroupsRouter."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

from snackbase.infrastructure.api.dependencies import CurrentUser
from snackbase.infrastructure.api.routes.groups_router import (
    add_user_to_group,
    create_group,
    delete_group,
    get_group,
    list_groups,
    router,
    update_group,
)
from snackbase.infrastructure.api.schemas.group_schemas import (
    GroupCreate,
    GroupUpdate,
    UserGroupUpdate,
)
from snackbase.infrastructure.persistence.models import GroupModel
from snackbase.infrastructure.persistence.repositories.group_repository import GroupRepository


@pytest.fixture
def mock_group_repo():
    """Create a mock GroupRepository."""
    return AsyncMock(spec=GroupRepository)


@pytest.fixture
def current_user():
    """Create a mock verified user."""
    return CurrentUser(
        user_id="user1",
        account_id="acc1",
        email="user@example.com",
        role="admin",
        groups=[],
    )


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_group(mock_group_repo, current_user, mock_session):
    """Test creating a group successfully."""
    group_data = GroupCreate(name="Devs", description="Developers")
    mock_group_repo.get_by_name_and_account.return_value = None
    mock_group_repo.create.return_value = GroupModel(
        id="g1", 
        name="Devs", 
        account_id="acc1",
        description="Developers"
    )

    result = await create_group(group_data, current_user, mock_group_repo, mock_session)

    assert result.name == "Devs"
    assert result.account_id == "acc1"
    mock_group_repo.create.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_group_duplicate(mock_group_repo, current_user, mock_session):
    """Test creating a duplicate group."""
    group_data = GroupCreate(name="Devs")
    mock_group_repo.get_by_name_and_account.return_value = GroupModel(id="g1")

    with pytest.raises(HTTPException) as exc:
        await create_group(group_data, current_user, mock_group_repo, mock_session)
    
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_list_groups(mock_group_repo, current_user):
    """Test listing groups."""
    mock_group_repo.list.return_value = [GroupModel(id="g1"), GroupModel(id="g2")]

    result = await list_groups(current_user, mock_group_repo)

    assert len(result) == 2
    mock_group_repo.list.assert_called_once_with("acc1", 0, 100)


@pytest.mark.asyncio
async def test_get_group(mock_group_repo, current_user):
    """Test getting a group."""
    mock_group_repo.get_by_id.return_value = GroupModel(id="g1", account_id="acc1")

    result = await get_group("g1", current_user, mock_group_repo)

    assert result.id == "g1"


@pytest.mark.asyncio
async def test_get_group_not_found(mock_group_repo, current_user):
    """Test getting a non-existent group."""
    mock_group_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_group("g1", current_user, mock_group_repo)
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_group_wrong_account(mock_group_repo, current_user):
    """Test getting a group from another account."""
    mock_group_repo.get_by_id.return_value = GroupModel(id="g1", account_id="acc2")

    with pytest.raises(HTTPException) as exc:
        await get_group("g1", current_user, mock_group_repo)
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_add_user_to_group(mock_group_repo, current_user, mock_session):
    """Test adding user to group."""
    group_id = "g1"
    user_data = UserGroupUpdate(user_id="u2")
    
    mock_group_repo.get_by_id.return_value = GroupModel(id=group_id, account_id="acc1")
    mock_group_repo.is_user_in_group.return_value = False

    await add_user_to_group(group_id, user_data, current_user, mock_group_repo, mock_session)

    mock_group_repo.add_user.assert_called_once_with(group_id, "u2")
    mock_session.commit.assert_called_once()
