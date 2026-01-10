"""Unit tests for the PasswordResetToken domain entity."""

import hashlib
from datetime import datetime, timedelta, timezone
from snackbase.domain.entities.password_reset import PasswordResetToken


def test_password_reset_token_generation():
    """Test generating a new password reset token."""
    user_id = "user-123"
    email = "user@example.com"
    expires_in = 3600

    entity, raw_token = PasswordResetToken.generate(user_id, email, expires_in)

    assert entity.user_id == user_id
    assert entity.email == email
    assert entity.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert entity.used_at is None
    
    # Check expiration (approximate)
    expected_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    assert abs((entity.expires_at - expected_expires_at).total_seconds()) < 5


def test_password_reset_token_is_valid():
    """Test the is_valid method."""
    user_id = "user-123"
    email = "user@example.com"
    
    # Valid token
    entity, _ = PasswordResetToken.generate(user_id, email, expires_in_seconds=3600)
    assert entity.is_valid() is True

    # Expired token
    expired_entity, _ = PasswordResetToken.generate(user_id, email, expires_in_seconds=-10)
    assert expired_entity.is_valid() is False

    # Used token
    used_entity, _ = PasswordResetToken.generate(user_id, email)
    used_entity.used_at = datetime.now(timezone.utc)
    assert used_entity.is_valid() is False
