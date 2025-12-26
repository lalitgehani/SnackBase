"""Unit tests for AccountService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.domain.services.account_service import AccountService
from snackbase.infrastructure.persistence.models import AccountModel


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def account_service(mock_session):
    """AccountService instance with mocked repository."""
    service = AccountService(mock_session)
    # Mock the internal repository instance directly
    service.account_repo = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_create_account_with_slug(account_service):
    """Create with explicit slug."""
    # Setup mocks
    account_service.account_repo.get_all_ids.return_value = []
    account_service.account_repo.slug_exists.return_value = False
    
    # Return what was passed (simplified)
    async def side_effect(account):
        return account
    account_service.account_repo.create.side_effect = side_effect

    # Execute
    result = await account_service.create_account(name="My Account", slug="custom-slug")

    # Verify
    assert result.name == "My Account"
    assert result.slug == "custom-slug"
    assert result.id == "AA0001"  # First ID generated
    
    account_service.account_repo.create.assert_called_once()
    account_service.account_repo.slug_exists.assert_called_with("custom-slug")


@pytest.mark.asyncio
async def test_create_account_auto_slug(account_service):
    """Create with auto-generated slug."""
    account_service.account_repo.get_all_ids.return_value = []
    account_service.account_repo.slug_exists.return_value = False  # Always available
    
    async def side_effect(account):
        return account
    account_service.account_repo.create.side_effect = side_effect

    # Execute
    result = await account_service.create_account(name="My Automatic Account")

    # Verify
    assert result.slug == "my-automatic-account"
    assert result.id == "AA0001"


@pytest.mark.asyncio
async def test_create_account_duplicate_slug(account_service):
    """Verify slug uniqueness validation."""
    account_service.account_repo.get_all_ids.return_value = []
    # Mock slug exists to return True for "taken"
    account_service.account_repo.slug_exists.return_value = True

    # Expect error when explicit slug is taken
    with pytest.raises(ValueError, match="already exists"):
        await account_service.create_account(name="Acme", slug="taken")


@pytest.mark.asyncio
async def test_update_account_success(account_service):
    """Update account name."""
    existing = AccountModel(id="AA0001", name="Old Name", slug="acc-1")
    account_service.account_repo.get_by_id.return_value = existing
    
    async def update_side_effect(account):
        return account
    account_service.account_repo.update.side_effect = update_side_effect

    # Execute
    result = await account_service.update_account("AA0001", "New Name")

    # Verify
    assert result.name == "New Name"
    account_service.account_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_account_not_found(account_service):
    """Verify error handling for update."""
    account_service.account_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await account_service.update_account("NONEXISTENT", "New Name")


@pytest.mark.asyncio
async def test_delete_account_success(account_service):
    """Delete account."""
    existing = AccountModel(id="AA0001", name="Delete Me")
    account_service.account_repo.get_by_id.return_value = existing

    await account_service.delete_account("AA0001")

    account_service.account_repo.delete.assert_called_once_with(existing)


@pytest.mark.asyncio
async def test_delete_system_account_prevented(account_service):
    """Prevent SY0000 deletion."""
    with pytest.raises(ValueError, match="Cannot delete system account"):
        await account_service.delete_account("SY0000")
    
    # Ensure delete was not called
    account_service.account_repo.delete.assert_not_called()


@pytest.mark.asyncio
async def test_list_accounts_paginated(account_service):
    """List with pagination."""
    # Mock return data
    mock_accounts = [
        AccountModel(id="AA0001", name="A1"),
        AccountModel(id="AA0002", name="A2")
    ]
    account_service.account_repo.get_all_paginated.return_value = (mock_accounts, 100)
    account_service.account_repo.get_user_count.return_value = 5  # Mock 5 users each

    # Execute
    results, total = await account_service.list_accounts(page=1)

    # Verify
    assert total == 100
    assert len(results) == 2
    # Verify each item is (account, user_count)
    assert results[0][0].id == "AA0001"
    assert results[0][1] == 5
    
    account_service.account_repo.get_all_paginated.assert_called_once()
