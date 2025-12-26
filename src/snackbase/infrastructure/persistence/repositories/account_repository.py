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

    async def get_all_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search_query: str | None = None,
    ) -> tuple[list[AccountModel], int]:
        """Get paginated list of accounts with optional search and sorting.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Column to sort by (id, slug, name, created_at).
            sort_order: Sort order (asc or desc).
            search_query: Optional search query (searches name, slug, ID).

        Returns:
            Tuple of (list of accounts, total count).
        """
        from sqlalchemy import func, or_

        # Build base query
        query = select(AccountModel)

        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    AccountModel.name.ilike(search_pattern),
                    AccountModel.slug.ilike(search_pattern),
                    AccountModel.id.ilike(search_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Apply sorting
        sort_column = getattr(AccountModel, sort_by, AccountModel.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        accounts = list(result.scalars().all())

        return accounts, total

    async def update(self, account: AccountModel) -> AccountModel:
        """Update an existing account.

        Args:
            account: Account model with updated fields.

        Returns:
            Updated account model.
        """
        await self.session.flush()
        await self.session.refresh(account)
        return account

    async def delete(self, account: AccountModel) -> None:
        """Delete an account.

        Args:
            account: Account model to delete.
        """
        await self.session.delete(account)
        await self.session.flush()

    async def get_user_count(self, account_id: str) -> int:
        """Get the number of users in an account.

        Args:
            account_id: Account ID.

        Returns:
            Number of users in the account.
        """
        from sqlalchemy import func

        from snackbase.infrastructure.persistence.models import UserModel

        result = await self.session.execute(
            select(func.count(UserModel.id)).where(UserModel.account_id == account_id)
        )
        return result.scalar_one() or 0

