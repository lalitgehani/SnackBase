"""Unit tests for UserRepository user management methods."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import UserModel
from snackbase.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session):
    """Create a UserRepository instance with a mock session."""
    return UserRepository(mock_session)


@pytest.fixture
def sample_user():
    """Create a sample user model."""
    return UserModel(
        id="usr_abc123xyz",
        email="user@example.com",
        account_id="AB1234",
        role_id=1,
        is_active=True,
        password_hash="hashed_password",
        created_at=None,
        last_login=None,
    )


@pytest.mark.asyncio
async def test_update(repository, mock_session, sample_user):
    """Test updating a user record."""
    # Setup the mock for refresh
    mock_session.refresh = AsyncMock()

    result = await repository.update(sample_user)

    mock_session.add.assert_called_once_with(sample_user)
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once_with(sample_user)
    assert result == sample_user


@pytest.mark.asyncio
async def test_soft_delete(repository, mock_session, sample_user):
    """Test soft deleting a user (setting is_active=False)."""
    user_id = "usr_abc123xyz"

    # Mock get_by_id to return the updated user
    updated_user = UserModel(
        id=user_id,
        email="user@example.com",
        account_id="AB1234",
        role_id=1,
        is_active=False,
        password_hash="hashed_password",
        created_at=None,
        last_login=None,
    )

    # Mock execute for update
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result

    # Mock get_by_id using the repository itself
    async def mock_get_by_id(uid):
        if uid == user_id:
            return updated_user
        return None

    repository.get_by_id = mock_get_by_id

    result = await repository.soft_delete(user_id)

    mock_session.execute.assert_called()
    mock_session.flush.assert_called()
    assert result is not None
    assert result.is_active is False


@pytest.mark.asyncio
async def test_soft_delete_not_found(repository, mock_session):
    """Test soft deleting a non-existent user."""
    user_id = "nonexistent_user"

    # Mock execute for update
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result

    # Mock get_by_id to return None
    async def mock_get_by_id(uid):
        return None

    repository.get_by_id = mock_get_by_id

    result = await repository.soft_delete(user_id)

    mock_session.execute.assert_called()
    assert result is None


@pytest.mark.asyncio
async def test_list_paginated_default(repository, mock_session, sample_user):
    """Test listing users with default parameters."""
    # Mock execute result for count query
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    # Mock execute result for users query
    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [sample_user]

    # Setup execute to return different results
    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return mock_count_result
        return mock_users_result

    mock_session.execute = mock_execute

    users, total = await repository.list_paginated()

    assert total == 1
    assert len(users) == 1
    assert users[0].id == sample_user.id


@pytest.mark.asyncio
async def test_list_paginated_with_filters(repository, mock_session, sample_user):
    """Test listing users with filters applied."""
    # Mock execute results - when filters exist, it uses subquery count (2 calls total)
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [sample_user]

    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return mock_count_result
        return mock_users_result

    mock_session.execute = mock_execute

    users, total = await repository.list_paginated(
        account_id="AB1234",
        role_id=1,
        is_active=True,
        search="user",
        skip=10,
        limit=20,
        sort_field="email",
        sort_desc=False,
    )

    assert total == 1
    assert len(users) == 1
    assert execute_call_count == 2


@pytest.mark.asyncio
async def test_list_paginated_empty_result(repository, mock_session):
    """Test listing users when no users match filters."""
    # Mock execute results - when filters exist, it uses subquery count (2 calls total)
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = []

    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return mock_count_result
        return mock_users_result

    mock_session.execute = mock_execute

    users, total = await repository.list_paginated(account_id="XX9999")

    assert total == 0
    assert len(users) == 0


@pytest.mark.asyncio
async def test_update_password(repository, mock_session, sample_user):
    """Test updating a user's password."""
    user_id = "usr_abc123xyz"
    new_password_hash = "new_hashed_password"

    # Mock get_by_id to return the updated user
    updated_user = UserModel(
        id=user_id,
        email="user@example.com",
        account_id="AB1234",
        role_id=1,
        is_active=True,
        password_hash=new_password_hash,
        created_at=None,
        last_login=None,
    )

    async def mock_get_by_id(uid):
        if uid == user_id:
            return updated_user
        return None

    repository.get_by_id = mock_get_by_id

    result = await repository.update_password(user_id, new_password_hash)

    mock_session.execute.assert_called()
    mock_session.flush.assert_called()
    assert result is not None
    assert result.password_hash == new_password_hash


@pytest.mark.asyncio
async def test_update_password_not_found(repository, mock_session):
    """Test updating password for a non-existent user."""
    user_id = "nonexistent_user"
    new_password_hash = "new_hashed_password"

    # Mock execute result
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result

    async def mock_get_by_id(uid):
        return None

    repository.get_by_id = mock_get_by_id

    result = await repository.update_password(user_id, new_password_hash)

    mock_session.execute.assert_called()
    mock_session.flush.assert_called()
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_refresh_tokens(repository, mock_session):
    """Test invalidating all refresh tokens for a user."""
    user_id = "usr_abc123xyz"

    # Mock execute result
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result

    await repository.invalidate_refresh_tokens(user_id)

    # Execute should be called to delete tokens
    assert mock_session.execute.call_count >= 1
    mock_session.flush.assert_called()


@pytest.mark.asyncio
async def test_list_paginated_with_sorting(repository, mock_session):
    """Test list_paginated with different sort options."""
    sample_user2 = UserModel(
        id="usr_def456",
        email="admin@example.com",
        account_id="AB1234",
        role_id=2,
        is_active=True,
        password_hash="hashed_password",
        created_at=None,
        last_login=None,
    )

    # Mock execute results
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 2

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [
        sample_user,
        sample_user2,
    ]

    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return mock_count_result
        return mock_users_result

    mock_session.execute = mock_execute

    # Test ascending sort
    users_asc, total = await repository.list_paginated(
        sort_field="email", sort_desc=False
    )

    assert total == 2
    assert len(users_asc) == 2


@pytest.mark.asyncio
async def test_list_paginated_with_search(repository, mock_session, sample_user):
    """Test list_paginated with search parameter."""
    # Mock execute results - search is a filter, so uses subquery count (2 calls total)
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [sample_user]

    execute_call_count = 0

    async def mock_execute(query):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return mock_count_result
        return mock_users_result

    mock_session.execute = mock_execute

    users, total = await repository.list_paginated(search="example")

    assert total == 1
    assert len(users) == 1
    assert "example" in users[0].email
