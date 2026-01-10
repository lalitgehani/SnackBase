"""Unit tests for EmailVerificationService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from snackbase.domain.entities.email_verification import EmailVerificationToken
from snackbase.domain.services.email_verification_service import EmailVerificationService
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
def mock_verification_repo():
    """Mock verification repository."""
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
def verification_service(
    mock_session, mock_user_repo, mock_verification_repo, mock_email_service
):
    """EmailVerificationService instance with mocked dependencies."""
    return EmailVerificationService(
        session=mock_session,
        user_repo=mock_user_repo,
        verification_repo=mock_verification_repo,
        email_service=mock_email_service,
    )


@pytest.mark.asyncio
async def test_send_verification_email_success(
    verification_service, mock_verification_repo, mock_email_service, mock_session
):
    """Test successful generation and sending of verification email."""
    # Setup
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"

    mock_email_service.send_template_email.return_value = True

    # Execute
    success = await verification_service.send_verification_email(user_id, email, account_id)

    # Verify
    assert success is True
    mock_verification_repo.delete_for_user_email.assert_called_once_with(user_id, email)
    mock_verification_repo.create.assert_called_once()
    mock_email_service.send_template_email.assert_called_once()
    mock_session.commit.assert_called_once()

    # Verify template variables
    call_args = mock_email_service.send_template_email.call_args[1]
    assert call_args["to"] == email
    assert call_args["template_type"] == "email_verification"
    assert "verification_url" in call_args["variables"]
    assert (
        "http://localhost:3000/verify-email?token="
        in call_args["variables"]["verification_url"]
    )


@pytest.mark.asyncio
async def test_send_verification_email_failure(
    verification_service, mock_email_service, mock_session
):
    """Test failure when email sending fails."""
    # Setup
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"

    mock_email_service.send_template_email.return_value = False

    # Execute
    success = await verification_service.send_verification_email(user_id, email, account_id)

    # Verify
    assert success is False
    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_verify_email_success(
    verification_service, mock_verification_repo, mock_user_repo, mock_session
):
    """Test successful email verification."""
    # Setup
    token_plain = "valid-token"
    user_id = "user-123"

    # Mock token
    token_entity = EmailVerificationToken(
        user_id=user_id,
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        id="token-id",
    )
    mock_verification_repo.get_by_token.return_value = token_entity

    # Mock user
    user_model = UserModel(id=user_id, email="test@example.com", account_id="acc-456")
    mock_user_repo.get_by_id.return_value = user_model

    # Execute
    result = await verification_service.verify_email(token_plain)

    # Verify
    assert result == user_model
    assert user_model.email_verified is True
    assert user_model.email_verified_at is not None
    mock_verification_repo.mark_as_used.assert_called_once_with("token-id")
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_invalid_token(
    verification_service, mock_verification_repo, mock_session
):
    """Test verification failure with invalid token."""
    # Setup
    mock_verification_repo.get_by_token.return_value = None

    # Execute
    result = await verification_service.verify_email("invalid-token")

    # Verify
    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_verify_email_expired_token(
    verification_service, mock_verification_repo, mock_session
):
    """Test verification failure with expired token."""
    # Setup
    token_entity = EmailVerificationToken(
        user_id="user-123",
        email="test@example.com",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        id="token-id",
    )
    mock_verification_repo.get_by_token.return_value = token_entity

    # Execute
    result = await verification_service.verify_email("expired-token")

    # Verify
    assert result is None
    mock_session.commit.assert_not_called()
