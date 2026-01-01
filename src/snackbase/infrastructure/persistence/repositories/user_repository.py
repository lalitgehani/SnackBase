"""User repository for database operations."""

from datetime import UTC, datetime

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

    async def get_by_external_id(
        self, auth_provider_name: str, external_id: str
    ) -> UserModel | None:
        """Get a user by their external provider ID.

        Args:
            auth_provider_name: Name of the OAuth/SAML provider (e.g., 'google').
            external_id: Unique identifier from the provider.

        Returns:
            User model if found, None otherwise.
        """
        result = await self.session.execute(
            select(UserModel).where(
                and_(
                    UserModel.auth_provider_name == auth_provider_name,
                    UserModel.external_id == external_id,
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
            .values(last_login=datetime.now(UTC))
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

    async def update(self, user: UserModel) -> UserModel:
        """Update a user record.

        Args:
            user: User model with updated fields.

        Returns:
            Updated user model.
        """
        self.session.add(user)
        await self.session.flush()
        # Refresh to get updated values from triggers (e.g., updated_at)
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user_id: str) -> UserModel | None:
        """Soft delete a user by setting is_active=False.

        Args:
            user_id: ID of the user to deactivate.

        Returns:
            Updated user model if found, None otherwise.
        """
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(is_active=False)
        )
        await self.session.flush()
        return await self.get_by_id(user_id)

    async def list_paginated(
        self,
        account_id: str | None = None,
        role_id: int | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 30,
        sort_field: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[UserModel], int]:
        """List users with optional filters and pagination.

        Args:
            account_id: Filter by account ID.
            role_id: Filter by role ID.
            is_active: Filter by active status.
            search: Search by email (case-insensitive partial match).
            skip: Number of records to skip (pagination offset).
            limit: Maximum number of records to return.
            sort_field: Field to sort by (default: created_at).
            sort_desc: Sort descending if True, ascending if False.

        Returns:
            Tuple of (list of users, total count).
        """
        from sqlalchemy import func
        from sqlalchemy.orm import selectinload

        # Build base query with eager loads
        query = select(UserModel).options(
            selectinload(UserModel.account),
            selectinload(UserModel.role),
        )

        # Build conditions
        conditions = []

        if account_id:
            conditions.append(UserModel.account_id == account_id)

        if role_id:
            conditions.append(UserModel.role_id == role_id)

        if is_active is not None:
            conditions.append(UserModel.is_active == is_active)

        if search:
            conditions.append(UserModel.email.ilike(f"%{search}%"))

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Get total count - use subquery when conditions exist for accurate count
        if conditions:
            # For filtered queries, count from subquery
            total = (await self.session.execute(
                select(func.count()).select_from(query.subquery())
            )).scalar_one() or 0
        else:
            # For unfiltered queries, count directly from table
            total = (await self.session.execute(
                select(func.count(UserModel.id))
            )).scalar_one() or 0

        # Apply sorting
        sort_column = getattr(UserModel, sort_field, UserModel.created_at)
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def update_password(self, user_id: str, password_hash: str) -> UserModel | None:
        """Update a user's password.

        Args:
            user_id: ID of the user to update.
            password_hash: New password hash (Argon2).

        Returns:
            Updated user model if found, None otherwise.
        """
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(password_hash=password_hash)
        )
        await self.session.flush()
        return await self.get_by_id(user_id)

    async def invalidate_refresh_tokens(self, user_id: str) -> None:
        """Delete all refresh tokens for a user.

        This forces the user to log in again on all devices.

        Args:
            user_id: ID of the user whose tokens to invalidate.
        """
        from snackbase.infrastructure.persistence.models import RefreshTokenModel

        await self.session.execute(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
        )
        # Delete all refresh tokens for the user
        await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id
            )
        )
        # Actually delete them
        from sqlalchemy import delete as sql_delete

        await self.session.execute(
            sql_delete(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id
            )
        )
        await self.session.flush()

