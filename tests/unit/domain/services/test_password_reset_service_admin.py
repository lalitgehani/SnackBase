"""Unit tests for superadmin-initiated password reset in PasswordResetService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import pytest

from snackbase.domain.entities.password_reset import PasswordResetToken
from snackbase.domain.services.password_reset_service import PasswordResetService
from snackbase.infrastructure.persistence.models import UserModel

@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    return AsyncMock()

@pytest.fixture
def mock_user_repo():
    """Mock user repository."""
    return AsyncMock()

@pytest.fixture
def mock_reset_repo():
    """Mock password reset repository."""
    return AsyncMock()

@pytest.fixture
def mock_refresh_token_repo():
    """Mock refresh token repository."""
    return AsyncMock()

@pytest.fixture
def mock_email_service():
    """Mock email service."""
    service = AsyncMock()
    service._get_system_variables = AsyncMock(
        return_value={"app_url": "http://localhost:3000"}
    )
    return service

@pytest.fixture
def reset_service(
    mock_session, mock_user_repo, mock_reset_repo, mock_refresh_token_repo, mock_email_service
):
    """PasswordResetService instance with mocked dependencies."""
    return PasswordResetService(
        session=mock_session,
        user_repo=mock_user_repo,
        reset_repo=mock_reset_repo,
        refresh_token_repo=mock_refresh_token_repo,
        email_service=mock_email_service,
    )

@pytest.mark.asyncio
async def test_send_reset_link_by_admin_success(
    reset_service, mock_refresh_token_repo, mock_email_service, mock_session
):
    """Test superadmin sending a reset link successfully."""
    # Setup
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"

    mock_email_service.send_template_email.return_value = True

    # Execute
    success = await reset_service.send_reset_link_by_admin(user_id, email, account_id)

    # Verify
    assert success is True
    # Verify refresh tokens were revoked
    mock_refresh_token_repo.revoke_all_for_user.assert_called_once_with(user_id, account_id)
    # Verify email was sent
    mock_email_service.send_template_email.assert_called_once()
    mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_set_password_by_admin_success(
    reset_service, mock_user_repo, mock_reset_repo, mock_refresh_token_repo, mock_session
):
    """Test superadmin setting a password directly."""
    # Setup
    user_id = "user-123"
    account_id = "acc-456"
    new_password = "NewSecurePassword123!"

    # Mock user
    user_model = UserModel(
        id=user_id,
        email="test@example.com",
        account_id=account_id,
        password_hash="old-hash"
    )
    mock_user_repo.get_by_id.return_value = user_model

    # Execute
    with patch("snackbase.domain.services.password_reset_service.hash_password") as mock_hash:
        mock_hash.return_value = "new-hashed-password"
        result = await reset_service.set_password_by_admin(user_id, new_password)

    # Verify
    assert result == user_model
    assert user_model.password_hash == "new-hashed-password"
    # Verify reset tokens for user were deleted
    mock_reset_repo.delete_for_user.assert_called_once_with(user_id)
    # Verify refresh tokens were revoked
    mock_refresh_token_repo.revoke_all_for_user.assert_called_once_with(user_id, account_id)
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_set_password_by_admin_user_not_found(reset_service, mock_user_repo):
    """Test superadmin setting a password for a non-existent user."""
    # Setup
    mock_user_repo.get_by_id.return_value = None

    # Execute & Verify
    with pytest.raises(ValueError, match="User with ID user-not-found not found"):
        await reset_service.set_password_by_admin("user-not-found", "password")
