"""User repository for database operations."""

from datetime import datetime, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import UserModel


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, user: UserModel) -> UserModel:
        """Create a new user.

        Args:
            user: User model to create.

        Returns:
            Created user model.
        """
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: str) -> UserModel | None:
        """Get a user by ID.

        Args:
            user_id: User ID (UUID string).

        Returns:
            User model if found, None otherwise.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_groups(self, user_id: str) -> UserModel | None:
        """Get a user by ID with groups eagerly loaded.

        Args:
            user_id: User ID (UUID string).

        Returns:
            User model with groups if found, None otherwise.
        """
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.groups))
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_account(
        self, email: str, account_id: str
    ) -> UserModel | None:
        """Get a user by email within a specific account.

        Args:
            email: User's email address.
            account_id: Account ID to search within.

        Returns:
            User model if found, None otherwise.
        """
        result = await self.session.execute(
            select(UserModel).where(
                and_(
                    UserModel.email == email,
                    UserModel.account_id == account_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def email_exists_in_account(self, email: str, account_id: str) -> bool:
        """Check if an email already exists within an account.

        Args:
            email: Email to check.
            account_id: Account ID to check within.

        Returns:
            True if email exists in account, False otherwise.
        """
        result = await self.session.execute(
            select(UserModel.id)
            .where(
                and_(
                    UserModel.email == email,
                    UserModel.account_id == account_id,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def update_last_login(self, user_id: str) -> None:
        """Update the last_login timestamp for a user.

        Args:
            user_id: ID of the user to update.
        """
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def count_all(self) -> int:
        """Count total number of users across all accounts.

        Returns:
            Total count of users.
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(UserModel.id)))
        return result.scalar_one() or 0

    async def count_created_since(self, since: datetime) -> int:
        """Count users created since a given datetime.

        Args:
            since: Datetime to count from.

        Returns:
            Count of users created since the given datetime.
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(UserModel.id)).where(UserModel.created_at >= since)
        )
        return result.scalar_one() or 0

    async def get_recent_registrations(self, limit: int = 10) -> list[UserModel]:
        """Get recent user registrations with account information.

        Args:
            limit: Maximum number of registrations to return.

        Returns:
            List of recent user models with account relationship loaded.
        """
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserModel)
            .options(selectinload(UserModel.account))
            .order_by(UserModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_account_paginated(
        self,
        account_id: str,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[UserModel], int]:
        """Get paginated list of users for a specific account.

        Args:
            account_id: Account ID to filter by.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (list of users, total count).
        """
        from sqlalchemy import func
        from sqlalchemy.orm import selectinload

        # Get total count
        count_result = await self.session.execute(
            select(func.count(UserModel.id)).where(UserModel.account_id == account_id)
        )
        total = count_result.scalar_one() or 0

        # Get paginated users
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.account_id == account_id)
            .options(selectinload(UserModel.role))
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        users = list(result.scalars().all())

        return users, total

