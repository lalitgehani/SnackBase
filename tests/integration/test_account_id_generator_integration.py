"""Integration tests for AccountIdGenerator with database.

Tests thread-safety and concurrent account creation scenarios.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.account_id_generator import AccountIdGenerator
from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.infrastructure.persistence.repositories.account_repository import (
    AccountRepository,
)


@pytest.mark.asyncio
class TestAccountIdGeneratorIntegration:
    """Integration tests for account ID generation with database."""

    async def test_generate_with_database(self, db_session: AsyncSession):
        """Test ID generation with actual database queries."""
        repo = AccountRepository(db_session)

        # Create first account
        account1 = AccountModel(
            id="AA0001",
            slug="test-account-1",
            name="Test Account 1",
        )
        await repo.create(account1)
        await db_session.commit()

        # Generate next ID
        existing_ids = await repo.get_all_ids()
        new_id = AccountIdGenerator.generate(existing_ids)
        assert new_id == "AA0002"

        # Create second account
        account2 = AccountModel(
            id=new_id,
            slug="test-account-2",
            name="Test Account 2",
        )
        await repo.create(account2)
        await db_session.commit()

        # Verify both accounts exist
        existing_ids = await repo.get_all_ids()
        assert len(existing_ids) == 2
        assert "AA0001" in existing_ids
        assert "AA0002" in existing_ids

    async def test_concurrent_account_creation(self, db_session: AsyncSession):
        """Test that concurrent account creation doesn't produce duplicates.

        Note: This test simulates concurrent creation. In production,
        database transaction isolation should prevent duplicates.
        """
        repo = AccountRepository(db_session)

        async def create_account(account_num: int) -> str:
            """Create an account and return its ID."""
            # Fetch existing IDs
            existing_ids = await repo.get_all_ids()

            # Generate new ID
            new_id = AccountIdGenerator.generate(existing_ids)

            # Create account
            account = AccountModel(
                id=new_id,
                slug=f"test-account-{account_num}",
                name=f"Test Account {account_num}",
            )
            await repo.create(account)
            await db_session.commit()

            return new_id

        # Create multiple accounts sequentially (simulating concurrent requests)
        # In a real scenario, these would be in separate transactions
        created_ids = []
        for i in range(5):
            account_id = await create_account(i)
            created_ids.append(account_id)

        # Verify all IDs are unique
        assert len(created_ids) == len(set(created_ids))

        # Verify all IDs are valid
        for account_id in created_ids:
            assert AccountIdGenerator.validate(account_id)

    async def test_restart_scenario(self, db_session: AsyncSession):
        """Test that generator works correctly after application restart."""
        repo = AccountRepository(db_session)

        # Create some accounts (simulating previous application run)
        initial_accounts = [
            AccountModel(id="AA0001", slug="account-1", name="Account 1"),
            AccountModel(id="AA0005", slug="account-5", name="Account 5"),
            AccountModel(id="AB0001", slug="account-ab1", name="Account AB1"),
        ]

        for account in initial_accounts:
            await repo.create(account)
        await db_session.commit()

        # Simulate application restart - fetch all IDs from database
        existing_ids = await repo.get_all_ids()
        assert len(existing_ids) == 3

        # Generate new ID (should continue from highest: AB0001 -> AB0002)
        new_id = AccountIdGenerator.generate(existing_ids)
        assert new_id == "AB0002"

        # Create new account
        new_account = AccountModel(
            id=new_id,
            slug="account-new",
            name="New Account",
        )
        await repo.create(new_account)
        await db_session.commit()

        # Verify total accounts
        all_ids = await repo.get_all_ids()
        assert len(all_ids) == 4
        assert new_id in all_ids

    async def test_collision_handling_with_database(self, db_session: AsyncSession):
        """Test that generator handles existing IDs correctly."""
        repo = AccountRepository(db_session)

        # Create accounts with gaps
        accounts = [
            AccountModel(id="AA0001", slug="account-1", name="Account 1"),
            AccountModel(id="AA0002", slug="account-2", name="Account 2"),
            AccountModel(id="AA0005", slug="account-5", name="Account 5"),
        ]

        for account in accounts:
            await repo.create(account)
        await db_session.commit()

        # Generate new ID
        existing_ids = await repo.get_all_ids()
        new_id = AccountIdGenerator.generate(existing_ids)

        # Should continue from highest (AA0005 -> AA0006)
        assert new_id == "AA0006"

    async def test_sy_prefix_ignored_in_database(self, db_session: AsyncSession):
        """Test that SY prefix is properly ignored when querying database."""
        repo = AccountRepository(db_session)

        # Create accounts including SY prefix (system accounts)
        accounts = [
            AccountModel(id="SY0001", slug="system-1", name="System Account 1"),
            AccountModel(id="SY9999", slug="system-max", name="System Account Max"),
            AccountModel(id="AA0001", slug="account-1", name="Account 1"),
        ]

        for account in accounts:
            await repo.create(account)
        await db_session.commit()

        # Generate new ID
        existing_ids = await repo.get_all_ids()
        new_id = AccountIdGenerator.generate(existing_ids)

        # Should continue from AA0001, not SY9999
        assert new_id == "AA0002"

    async def test_letter_pair_overflow_with_database(self, db_session: AsyncSession):
        """Test letter pair overflow with database."""
        repo = AccountRepository(db_session)

        # Create account at boundary
        account = AccountModel(
            id="AA9999",
            slug="account-boundary",
            name="Boundary Account",
        )
        await repo.create(account)
        await db_session.commit()

        # Generate new ID
        existing_ids = await repo.get_all_ids()
        new_id = AccountIdGenerator.generate(existing_ids)

        # Should overflow to next letter pair
        assert new_id == "AB0000"

        # Create the new account
        new_account = AccountModel(
            id=new_id,
            slug="account-overflow",
            name="Overflow Account",
        )
        await repo.create(new_account)
        await db_session.commit()

        # Verify both exist
        all_ids = await repo.get_all_ids()
        assert "AA9999" in all_ids
        assert "AB0000" in all_ids
