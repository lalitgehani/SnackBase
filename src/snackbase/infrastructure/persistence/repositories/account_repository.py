"""Account repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel


class AccountRepository:
    """Repository for account database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, account: AccountModel) -> AccountModel:
        """Create a new account.

        Args:
            account: Account model to create.

        Returns:
            Created account model.
        """
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(self, account_id: str) -> AccountModel | None:
        """Get an account by ID.

        Args:
            account_id: Account ID in XX#### format.

        Returns:
            Account model if found, None otherwise.
        """
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> AccountModel | None:
        """Get an account by slug.

        Args:
            slug: URL-friendly account identifier.

        Returns:
            Account model if found, None otherwise.
        """
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if an account slug already exists.

        Args:
            slug: Slug to check.

        Returns:
            True if slug exists, False otherwise.
        """
        result = await self.session.execute(
            select(AccountModel.id).where(AccountModel.slug == slug).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_all_ids(self) -> list[str]:
        """Get all account IDs.

        Used for account ID generation to avoid collisions.

        Returns:
            List of all account IDs.
        """
        result = await self.session.execute(select(AccountModel.id))
        return list(result.scalars().all())

    async def get_by_slug_or_id(self, identifier: str) -> AccountModel | None:
        """Get an account by slug or ID (XX#### format).

        Attempts to find by ID first (if format matches XX####), then by slug.

        Args:
            identifier: Account slug or ID.

        Returns:
            Account model if found, None otherwise.
        """
        import re

        # Check if identifier matches account ID format (2 letters + 4 digits)
        if re.match(r"^[A-Z]{2}\d{4}$", identifier.upper()):
            account = await self.get_by_id(identifier.upper())
            if account:
                return account

        # Fall back to slug lookup (case-insensitive)
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.slug == identifier.lower())
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        """Count total number of accounts.

        Returns:
            Total count of accounts.
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(AccountModel.id)))
        return result.scalar_one() or 0

    async def count_created_since(self, since: "datetime") -> int:
        """Count accounts created since a given datetime.

        Args:
            since: Datetime to count from.

        Returns:
            Count of accounts created since the given datetime.
        """
        from datetime import datetime
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(AccountModel.id)).where(AccountModel.created_at >= since)
        )
        return result.scalar_one() or 0

