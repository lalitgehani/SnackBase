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

