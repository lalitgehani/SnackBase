"""Service for creating and managing superadmin users.

Superadmin users are special users linked to the system account (SY0000)
that have full access to all accounts and system operations.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services import default_password_validator
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.auth import hash_password


class SuperadminCreationError(Exception):
    """Raised when superadmin creation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SuperadminService:
    """Service for managing superadmin users.

    Superadmin users are linked to the system account (SY0000) and have
    full access to all accounts and system operations.
    """

    @staticmethod
    async def create_system_account(
        session: AsyncSession,
    ) -> tuple[str, str]:
        """Create the system account if it doesn't exist.

        Args:
            session: Database session.

        Returns:
            Tuple of (account_id, slug) for the system account.

        Raises:
            SuperadminCreationError: If account creation fails.
        """
        from snackbase.infrastructure.persistence.models import AccountModel
        from snackbase.infrastructure.persistence.repositories import (
            AccountRepository,
        )

        account_repo = AccountRepository(session)

        # Check if system account already exists
        existing = await account_repo.get_by_id(SYSTEM_ACCOUNT_ID)
        if existing:
            return existing.id, existing.slug

        # Create system account
        account = AccountModel(
            id=SYSTEM_ACCOUNT_ID,
            slug="system",
            name="SnackBase System",
        )
        try:
            await account_repo.create(account)
            await session.commit()
            await session.refresh(account)
            return account.id, account.slug
        except Exception as e:
            await session.rollback()
            raise SuperadminCreationError(f"Failed to create system account: {e}") from e

    @staticmethod
    async def create_superadmin(
        email: str,
        password: str,
        session: AsyncSession,
    ) -> tuple[str, str]:
        """Create a superadmin user in the system account.

        Args:
            email: Email address for the superadmin.
            password: Password for the superadmin.
            session: Database session.

        Returns:
            Tuple of (user_id, account_id) for the created superadmin.

        Raises:
            SuperadminCreationError: If creation fails due to validation or database errors.
        """
        from snackbase.infrastructure.persistence.models import AccountModel, UserModel
        from snackbase.infrastructure.persistence.repositories import (
            AccountRepository,
            RoleRepository,
            UserRepository,
        )

        # Validate password strength
        password_errors = default_password_validator.validate(password)
        if password_errors:
            error_messages = [f"{e.field}: {e.message}" for e in password_errors]
            raise SuperadminCreationError(
                f"Password validation failed: {'; '.join(error_messages)}"
            )

        # Ensure system account exists
        account_id, _ = await SuperadminService.create_system_account(session)

        account_repo = AccountRepository(session)
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)

        # Check if superadmin with this email already exists
        existing_user = await user_repo.get_by_email_and_account(email, account_id)
        if existing_user:
            raise SuperadminCreationError(
                f"A superadmin with email '{email}' already exists"
            )

        # Get admin role
        admin_role = await role_repo.get_by_name("admin")
        if admin_role is None:
            raise SuperadminCreationError("Admin role not found in database")

        # Hash password
        password_hash = hash_password(password)

        # Create superadmin user
        user = UserModel(
            id=str(uuid.uuid4()),
            account_id=account_id,
            email=email,
            password_hash=password_hash,
            role_id=admin_role.id,
            is_active=True,
        )

        try:
            await user_repo.create(user)
            await session.commit()
            await session.refresh(user)
            return user.id, user.account_id
        except Exception as e:
            await session.rollback()
            raise SuperadminCreationError(f"Failed to create superadmin user: {e}") from e

    @staticmethod
    async def ensure_system_account_exists(session: AsyncSession) -> bool:
        """Ensure the system account exists, creating it if necessary.

        Args:
            session: Database session.

        Returns:
            True if system account exists or was created successfully.
        """
        from snackbase.infrastructure.persistence.repositories import (
            AccountRepository,
        )

        account_repo = AccountRepository(session)
        existing = await account_repo.get_by_id(SYSTEM_ACCOUNT_ID)
        if existing:
            return True

        await SuperadminService.create_system_account(session)
        return True

    @staticmethod
    async def has_superadmin(session: AsyncSession) -> bool:
        """Check if any superadmin users exist in the system account.

        Args:
            session: Database session.

        Returns:
            True if at least one superadmin exists, False otherwise.
        """
        from sqlalchemy import select
        from snackbase.infrastructure.persistence.models import UserModel

        result = await session.execute(
            select(UserModel).where(UserModel.account_id == SYSTEM_ACCOUNT_ID)
        )
        return result.first() is not None
