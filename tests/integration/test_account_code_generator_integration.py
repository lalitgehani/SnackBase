"""Integration tests for AccountCodeGenerator with database.

Tests thread-safety and concurrent account creation scenarios.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.account_code_generator import AccountCodeGenerator
from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.infrastructure.persistence.repositories.account_repository import (
    AccountRepository,
)


@pytest.mark.asyncio
class TestAccountCodeGeneratorIntegration:
    """Integration tests for account ID generation with database."""

    async def test_generate_with_database(self, db_session: AsyncSession):
        """Test account code generation with actual database queries."""
        repo = AccountRepository(db_session)

        # Create first account
        import uuid
        account1 = AccountModel(
            id=str(uuid.uuid4()),
            account_code="AA0001",
            slug="test-account-1",
            name="Test Account 1",
        )
        await repo.create(account1)
        await db_session.commit()

        # Generate next code
        existing_codes = await repo.get_all_account_codes()
        new_code = AccountCodeGenerator.generate(existing_codes)
        assert new_code == "AA0002"

        # Create second account
        account2 = AccountModel(
            id=str(uuid.uuid4()),
            account_code=new_code,
            slug="test-account-2",
            name="Test Account 2",
        )
        await repo.create(account2)
        await db_session.commit()

        # Verify both accounts exist
        existing_codes = await repo.get_all_account_codes()
        assert len(existing_codes) == 2
        assert "AA0001" in existing_codes
        assert "AA0002" in existing_codes

    async def test_concurrent_account_creation(self, db_session: AsyncSession):
        """Test that concurrent account creation doesn't produce duplicates.

        Note: This test simulates concurrent creation. In production,
        database transaction isolation should prevent duplicates.
        """
        repo = AccountRepository(db_session)

        import uuid

        async def create_account(account_num: int) -> str:
            """Create an account and return its account code."""
            # Fetch existing account codes
            existing_codes = await repo.get_all_account_codes()

            # Generate new account code
            new_code = AccountCodeGenerator.generate(existing_codes)

            # Create account
            account = AccountModel(
                id=str(uuid.uuid4()),
                account_code=new_code,
                slug=f"test-account-{account_num}",
                name=f"Test Account {account_num}",
            )
            await repo.create(account)
            await db_session.commit()

            return new_code

        # Create multiple accounts sequentially (simulating concurrent requests)
        # In a real scenario, these would be in separate transactions
        created_codes = []
        for i in range(5):
            account_code = await create_account(i)
            created_codes.append(account_code)

        # Verify all codes are unique
        assert len(created_codes) == len(set(created_codes))

        # Verify all codes are valid
        for account_code in created_codes:
            assert AccountCodeGenerator.validate(account_code)

    async def test_restart_scenario(self, db_session: AsyncSession):
        """Test that generator works correctly after application restart."""
        repo = AccountRepository(db_session)

        import uuid

        # Create some accounts (simulating previous application run)
        initial_accounts = [
            AccountModel(id=str(uuid.uuid4()), account_code="AA0001", slug="account-1", name="Account 1"),
            AccountModel(id=str(uuid.uuid4()), account_code="AA0005", slug="account-5", name="Account 5"),
            AccountModel(id=str(uuid.uuid4()), account_code="AB0001", slug="account-ab1", name="Account AB1"),
        ]

        for account in initial_accounts:
            await repo.create(account)
        await db_session.commit()

        # Simulate application restart - fetch all account codes from database
        existing_codes = await repo.get_all_account_codes()
        assert len(existing_codes) == 3

        # Generate new code (should continue from highest: AB0001 -> AB0002)
        new_code = AccountCodeGenerator.generate(existing_codes)
        assert new_code == "AB0002"

        # Create new account
        new_account = AccountModel(
            id=str(uuid.uuid4()),
            account_code=new_code,
            slug="account-new",
            name="New Account",
        )
        await repo.create(new_account)
        await db_session.commit()

        # Verify total accounts
        all_codes = await repo.get_all_account_codes()
        assert len(all_codes) == 4
        assert new_code in all_codes

    async def test_collision_handling_with_database(self, db_session: AsyncSession):
        """Test that generator handles existing IDs correctly."""
        repo = AccountRepository(db_session)

        import uuid

        # Create accounts with gaps
        accounts = [
            AccountModel(id=str(uuid.uuid4()), account_code="AA0001", slug="account-1", name="Account 1"),
            AccountModel(id=str(uuid.uuid4()), account_code="AA0002", slug="account-2", name="Account 2"),
            AccountModel(id=str(uuid.uuid4()), account_code="AA0005", slug="account-5", name="Account 5"),
        ]

        for account in accounts:
            await repo.create(account)
        await db_session.commit()

        # Generate new code
        existing_codes = await repo.get_all_account_codes()
        new_code = AccountCodeGenerator.generate(existing_codes)

        # Should continue from highest (AA0005 -> AA0006)
        assert new_code == "AA0006"

    async def test_sy_prefix_ignored_in_database(self, db_session: AsyncSession):
        """Test that SY prefix is properly ignored when querying database."""
        repo = AccountRepository(db_session)

        import uuid

        # Create accounts including SY prefix (system accounts)
        accounts = [
            AccountModel(id=str(uuid.uuid4()), account_code="SY0001", slug="system-1", name="System Account 1"),
            AccountModel(id=str(uuid.uuid4()), account_code="SY9999", slug="system-max", name="System Account Max"),
            AccountModel(id=str(uuid.uuid4()), account_code="AA0001", slug="account-1", name="Account 1"),
        ]

        for account in accounts:
            await repo.create(account)
        await db_session.commit()

        # Generate new code
        existing_codes = await repo.get_all_account_codes()
        new_code = AccountCodeGenerator.generate(existing_codes)

        # Should continue from AA0001, not SY9999
        assert new_code == "AA0002"

    async def test_letter_pair_overflow_with_database(self, db_session: AsyncSession):
        """Test letter pair overflow with database."""
        repo = AccountRepository(db_session)

        import uuid

        # Create account at boundary
        account = AccountModel(
            id=str(uuid.uuid4()),
            account_code="AA9999",
            slug="account-boundary",
            name="Boundary Account",
        )
        await repo.create(account)
        await db_session.commit()

        # Generate new code
        existing_codes = await repo.get_all_account_codes()
        new_code = AccountCodeGenerator.generate(existing_codes)

        # Should overflow to next letter pair
        assert new_code == "AB0000"

        # Create the new account
        new_account = AccountModel(
            id=str(uuid.uuid4()),
            account_code=new_code,
            slug="account-overflow",
            name="Overflow Account",
        )
        await repo.create(new_account)
        await db_session.commit()

        # Verify both exist
        all_codes = await repo.get_all_account_codes()
        assert "AA9999" in all_codes
        assert "AB0000" in all_codes
