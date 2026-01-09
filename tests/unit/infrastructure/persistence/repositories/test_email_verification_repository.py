"""Unit tests for email verification data model and repository."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from snackbase.domain.entities.email_verification import EmailVerificationToken
from snackbase.infrastructure.persistence.repositories.email_verification_repository import EmailVerificationRepository
from snackbase.infrastructure.persistence.models.email_verification import EmailVerificationTokenModel


def test_email_verification_token_generate():
    """Test generating a verification token."""
    user_id = "user-123"
    email = "test@example.com"
    entity, raw_token = EmailVerificationToken.generate(user_id, email)

    assert entity.user_id == user_id
    assert entity.email == email
    assert entity.token_hash is not None
    assert entity.expires_at > datetime.now(timezone.utc)
    assert entity.used_at is None
    assert raw_token is not None
    assert len(raw_token) > 0


def test_email_verification_token_is_valid():
    """Test token validity logic."""
    entity = EmailVerificationToken(
        user_id="u1",
        email="e1",
        token_hash="h1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    assert entity.is_valid() is True

    # Test expired
    entity.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    assert entity.is_valid() is False

    # Test used
    entity.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    entity.used_at = datetime.now(timezone.utc)
    assert entity.is_valid() is False


@pytest.mark.asyncio
async def test_repository_create():
    """Test repository create operation."""
    session = AsyncMock()
    session.add = MagicMock()
    repo = EmailVerificationRepository(session)
    
    entity = EmailVerificationToken(
        user_id="u1",
        email="e1",
        token_hash="h1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    await repo.create(entity)
    
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_repository_get_by_token():
    """Test repository get_by_token operation."""
    session = AsyncMock()
    repo = EmailVerificationRepository(session)
    
    raw_token = "secret-token"
    token_hash = repo._hash_token(raw_token)
    
    mock_model = EmailVerificationTokenModel(
        id="t1",
        user_id="u1",
        email="e1",
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        created_at=datetime.now(timezone.utc)
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    session.execute.return_value = mock_result
    
    result = await repo.get_by_token(raw_token)
    
    assert result is not None
    assert result.token_hash == token_hash
    assert result.user_id == "u1"


@pytest.mark.asyncio
async def test_repository_mark_as_used():
    """Test repository mark_as_used operation."""
    session = AsyncMock()
    repo = EmailVerificationRepository(session)
    
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session.execute.return_value = mock_result
    
    success = await repo.mark_as_used("t1")
    
    assert success is True
    session.execute.assert_called_once()
