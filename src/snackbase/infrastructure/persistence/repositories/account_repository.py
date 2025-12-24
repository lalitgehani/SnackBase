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
