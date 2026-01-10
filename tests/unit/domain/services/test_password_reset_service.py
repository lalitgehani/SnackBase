"""Unit tests for PasswordResetService."""

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
    # Mock _get_system_variables
    service._get_system_variables = AsyncMock(
        return_value={
            "app_name": "SnackBase",
            "app_url": "http://localhost:3000",
            "support_email": "support@snackbase.io",
        }
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
async def test_send_reset_email_success(
    reset_service, mock_reset_repo, mock_email_service, mock_session
):
    """Test successful generation and sending of password reset email."""
    # Setup
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"

    mock_email_service.send_template_email.return_value = True

    # Execute
    success = await reset_service.send_reset_email(user_id, email, account_id)

    # Verify
    assert success is True
    mock_reset_repo.create.assert_called_once()
    mock_email_service.send_template_email.assert_called_once()
    mock_session.commit.assert_called_once()

    # Verify template variables
    call_args = mock_email_service.send_template_email.call_args[1]
    assert call_args["to"] == email
    assert call_args["template_type"] == "password_reset"
    assert "reset_url" in call_args["variables"]
    assert (
        "http://localhost:3000/reset-password?token="
        in call_args["variables"]["reset_url"]
    )


@pytest.mark.asyncio
async def test_send_reset_email_failure(
    reset_service, mock_email_service, mock_session
):
    """Test failure when email sending fails."""
    # Setup
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"

    mock_email_service.send_template_email.return_value = False

    # Execute
    success = await reset_service.send_reset_email(user_id, email, account_id)

    # Verify
    assert success is False
    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_reset_password_success(
    reset_service, mock_reset_repo, mock_user_repo, mock_refresh_token_repo, mock_session
):
    """Test successful password reset."""
    # Setup
    token_plain = "valid-token"
    new_password = "new-secure-password"
    user_id = "user-123"
    account_id = "acc-456"

    # Mock token
    token_entity = PasswordResetToken(
        user_id=user_id,
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        id="token-id",
    )
    mock_reset_repo.get_by_token.return_value = token_entity

    # Mock user
    user_model = UserModel(
        id=user_id, 
        email="test@example.com", 
        account_id=account_id,
        password_hash="old-hash"
    )
    mock_user_repo.get_by_id.return_value = user_model

    # Mock refresh token revocation
    mock_refresh_token_repo.revoke_all_for_user.return_value = 2

    # Execute
    with patch("snackbase.domain.services.password_reset_service.hash_password") as mock_hash:
        mock_hash.return_value = "new-hashed-password"
        result = await reset_service.reset_password(token_plain, new_password)

    # Verify
    assert result == user_model
    assert user_model.password_hash == "new-hashed-password"
    mock_reset_repo.mark_as_used.assert_called_once_with("token-id")
    mock_refresh_token_repo.revoke_all_for_user.assert_called_once_with(user_id, account_id)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(
    reset_service, mock_reset_repo, mock_session
):
    """Test password reset failure with invalid token."""
    # Setup
    mock_reset_repo.get_by_token.return_value = None

    # Execute
    result = await reset_service.reset_password("invalid-token", "new-password")

    # Verify
    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_reset_password_expired_token(
    reset_service, mock_reset_repo, mock_session
):
    """Test password reset failure with expired token."""
    # Setup
    token_entity = PasswordResetToken(
        user_id="user-123",
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        id="token-id",
    )
    mock_reset_repo.get_by_token.return_value = token_entity

    # Execute
    result = await reset_service.reset_password("expired-token", "new-password")

    # Verify
    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_reset_password_used_token(
    reset_service, mock_reset_repo, mock_session
):
    """Test password reset failure with already used token."""
    # Setup
    token_entity = PasswordResetToken(
        user_id="user-123",
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        id="token-id",
        used_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    mock_reset_repo.get_by_token.return_value = token_entity

    # Execute
    result = await reset_service.reset_password("used-token", "new-password")

    # Verify
    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_verify_reset_token_valid(reset_service, mock_reset_repo):
    """Test token verification with valid token."""
    # Setup
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token_entity = PasswordResetToken(
        user_id="user-123",
        email="test@example.com",
        token_hash="hash",
        expires_at=expires_at,
        id="token-id",
    )
    mock_reset_repo.get_by_token.return_value = token_entity

    # Execute
    is_valid, returned_expires_at = await reset_service.verify_reset_token("valid-token")

    # Verify
    assert is_valid is True
    assert returned_expires_at == expires_at


@pytest.mark.asyncio
async def test_verify_reset_token_invalid(reset_service, mock_reset_repo):
    """Test token verification with invalid token."""
    # Setup
    mock_reset_repo.get_by_token.return_value = None

    # Execute
    is_valid, expires_at = await reset_service.verify_reset_token("invalid-token")

    # Verify
    assert is_valid is False
    assert expires_at is None


@pytest.mark.asyncio
async def test_verify_reset_token_expired(reset_service, mock_reset_repo):
    """Test token verification with expired token."""
    # Setup
    token_entity = PasswordResetToken(
        user_id="user-123",
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        id="token-id",
    )
    mock_reset_repo.get_by_token.return_value = token_entity

    # Execute
    is_valid, expires_at = await reset_service.verify_reset_token("expired-token")

    # Verify
    assert is_valid is False
    assert expires_at is None
