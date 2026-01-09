"""Unit tests for SuperadminService.

Tests the creation and management of superadmin users linked to the
system account (SY0000).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.superadmin_service import (
    SuperadminCreationError,
    SuperadminService,
)
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID


class TestCreateSystemAccount:
    """Test system account creation."""

    @pytest.mark.asyncio
    async def test_create_system_account_new(self):
        """Should create system account when it doesn't exist."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_account_repo = MagicMock()

        # Account doesn't exist
        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ):
            account_id, slug = await SuperadminService.create_system_account(mock_session)

        assert account_id == SYSTEM_ACCOUNT_ID
        assert slug == "system"
        mock_account_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_system_account_existing(self):
        """Should return existing system account without creating new one."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_account_repo = MagicMock()
        mock_existing_account = MagicMock()
        mock_existing_account.id = SYSTEM_ACCOUNT_ID
        mock_existing_account.slug = "system"

        # Account exists
        mock_account_repo.get_by_id = AsyncMock(return_value=mock_existing_account)

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ):
            account_id, slug = await SuperadminService.create_system_account(mock_session)

        assert account_id == SYSTEM_ACCOUNT_ID
        assert slug == "system"
        mock_account_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_system_account_failure(self):
        """Should raise SuperadminCreationError on database failure."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_account_repo = MagicMock()

        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ):
            with pytest.raises(SuperadminCreationError) as exc_info:
                await SuperadminService.create_system_account(mock_session)

        assert "Failed to create system account" in str(exc_info.value)


class TestCreateSuperadmin:
    """Test superadmin user creation."""

    @pytest.mark.asyncio
    async def test_create_superadmin_success(self):
        """Should create superadmin with valid email and password."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_user_repo = MagicMock()
        mock_role_repo = MagicMock()
        mock_account_repo = MagicMock()

        # Setup mocks
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role_repo.get_by_name = AsyncMock(return_value=mock_role)
        mock_user_repo.get_by_email_and_account = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock()
        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.RoleRepository",
            return_value=mock_role_repo,
        ):
            user_id, account_id = await SuperadminService.create_superadmin(
                email="admin@example.com",
                password="SecureP@ss123!",
                session=mock_session,
            )

        assert account_id == SYSTEM_ACCOUNT_ID
        assert user_id is not None
        mock_user_repo.create.assert_called_once()
        
        # Verify user attributes
        created_user = mock_user_repo.create.call_args[0][0]
        assert created_user.email_verified is True
        assert created_user.email_verified_at is not None

    @pytest.mark.asyncio
    async def test_create_superadmin_weak_password(self):
        """Should raise error for weak password."""
        mock_session = MagicMock(spec=AsyncSession)

        with pytest.raises(SuperadminCreationError) as exc_info:
            await SuperadminService.create_superadmin(
                email="admin@example.com",
                password="weak",
                session=mock_session,
            )

        assert "Password validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_superadmin_duplicate_email(self):
        """Should raise error when superadmin with email already exists."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_user_repo = MagicMock()
        mock_role_repo = MagicMock()
        mock_account_repo = MagicMock()

        mock_existing_user = MagicMock()
        mock_user_repo.get_by_email_and_account = AsyncMock(return_value=mock_existing_user)
        mock_role_repo.get_by_name = AsyncMock(return_value=MagicMock(id=1))
        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.RoleRepository",
            return_value=mock_role_repo,
        ):
            with pytest.raises(SuperadminCreationError) as exc_info:
                await SuperadminService.create_superadmin(
                    email="admin@example.com",
                    password="SecureP@ss123!",
                    session=mock_session,
                )

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_superadmin_no_admin_role(self):
        """Should raise error when admin role doesn't exist."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_user_repo = MagicMock()
        mock_role_repo = MagicMock()
        mock_account_repo = MagicMock()

        mock_role_repo.get_by_name = AsyncMock(return_value=None)
        mock_user_repo.get_by_email_and_account = AsyncMock(return_value=None)
        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "snackbase.infrastructure.persistence.repositories.RoleRepository",
            return_value=mock_role_repo,
        ):
            with pytest.raises(SuperadminCreationError) as exc_info:
                await SuperadminService.create_superadmin(
                    email="admin@example.com",
                    password="SecureP@ss123!",
                    session=mock_session,
                )

        assert "Admin role not found" in str(exc_info.value)


class TestEnsureSystemAccountExists:
    """Test ensuring system account exists."""

    @pytest.mark.asyncio
    async def test_ensure_system_account_exists_already(self):
        """Should return True when system account already exists."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_account_repo = MagicMock()
        mock_existing_account = MagicMock()

        mock_account_repo.get_by_id = AsyncMock(return_value=mock_existing_account)

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ):
            result = await SuperadminService.ensure_system_account_exists(mock_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_system_account_creates_if_missing(self):
        """Should create system account if it doesn't exist."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_account_repo = MagicMock()

        mock_account_repo.get_by_id = AsyncMock(return_value=None)
        mock_account_repo.create = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "snackbase.infrastructure.persistence.repositories.AccountRepository",
            return_value=mock_account_repo,
        ):
            result = await SuperadminService.ensure_system_account_exists(mock_session)

        assert result is True
        mock_account_repo.create.assert_called_once()


class TestHasSuperadmin:
    """Test checking if superadmin exists."""

    @pytest.mark.asyncio
    async def test_has_superadmin_true(self):
        """Should return True when superadmin exists."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock()  # User exists

        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await SuperadminService.has_superadmin(mock_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_superadmin_false(self):
        """Should return False when no superadmin exists."""
        mock_session = MagicMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.first.return_value = None  # No user

        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await SuperadminService.has_superadmin(mock_session)

        assert result is False


class TestSuperadminCreationError:
    """Test SuperadminCreationError exception."""

    def test_error_message(self):
        """Should store and display error message."""
        error = SuperadminCreationError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
