"""Unit tests for the PasswordResetRepository."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from snackbase.domain.entities.password_reset import PasswordResetToken
from snackbase.infrastructure.persistence.models.password_reset import PasswordResetTokenModel
from snackbase.infrastructure.persistence.repositories.password_reset_repository import PasswordResetRepository


@pytest.fixture
def repository(db_session: AsyncSession):
    """Create a PasswordResetRepository instance."""
    return PasswordResetRepository(db_session)


@pytest.mark.asyncio
async def test_repository_create(repository, db_session):
    """Test creating a new password reset token."""
    user_id = "user-123"
    email = "user@example.com"
    entity, _ = PasswordResetToken.generate(user_id, email)

    stored_entity = await repository.create(entity)

    assert stored_entity.id == entity.id
    assert stored_entity.user_id == user_id
    assert stored_entity.email == email
    assert stored_entity.token_hash == entity.token_hash

    # Verify in DB
    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity.id)
    result = await db_session.execute(stmt)
    model = result.scalar_one_or_none()
    assert model is not None
    assert model.user_id == user_id


@pytest.mark.asyncio
async def test_repository_get_by_token(repository):
    """Test retrieving a token by its plain text value."""
    user_id = "user-123"
    email = "user@example.com"
    entity, raw_token = PasswordResetToken.generate(user_id, email)
    await repository.create(entity)

    found_entity = await repository.get_by_token(raw_token)

    assert found_entity is not None
    assert found_entity.id == entity.id
    assert found_entity.user_id == user_id

    # Test non-existent token
    not_found = await repository.get_by_token("wrong-token")
    assert not_found is None


@pytest.mark.asyncio
async def test_repository_mark_as_used(repository, db_session):
    """Test marking a token as used."""
    user_id = "user-123"
    email = "user@example.com"
    entity, _ = PasswordResetToken.generate(user_id, email)
    await repository.create(entity)

    success = await repository.mark_as_used(entity.id)
    assert success is True

    # Verify in DB
    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity.id)
    result = await db_session.execute(stmt)
    model = result.scalar_one_or_none()
    assert model.used_at is not None


@pytest.mark.asyncio
async def test_repository_delete_for_user_email(repository, db_session):
    """Test deleting tokens for a user/email (invalidation)."""
    user_id = "user-123"
    email = "user@example.com"
    
    # Create first token
    entity1, _ = PasswordResetToken.generate(user_id, email)
    await repository.create(entity1)
    
    # Create second token (should delete the first)
    entity2, _ = PasswordResetToken.generate(user_id, email)
    await repository.create(entity2)

    # Verify first token is gone
    stmt1 = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity1.id)
    result1 = await db_session.execute(stmt1)
    assert result1.scalar_one_or_none() is None

    # Verify second token exists
    stmt2 = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity2.id)
    result2 = await db_session.execute(stmt2)
    assert result2.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_repository_delete_expired(repository, db_session):
    """Test deleting expired tokens."""
    user_id = "user-123"
    
    # Valid token
    entity1, _ = PasswordResetToken.generate(user_id, "user1@example.com", expires_in_seconds=3600)
    await repository.create(entity1)
    
    # Expired token (we manually set expires_at)
    entity2, _ = PasswordResetToken.generate(user_id, "user2@example.com", expires_in_seconds=-3600)
    await repository.create(entity2)

    deleted_count = await repository.delete_expired()
    assert deleted_count == 1

    # Verify in DB
    stmt1 = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity1.id)
    result1 = await db_session.execute(stmt1)
    assert result1.scalar_one_or_none() is not None

    stmt2 = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == entity2.id)
    result2 = await db_session.execute(stmt2)
    assert result2.scalar_one_or_none() is None
