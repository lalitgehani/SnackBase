"""Repository for password reset token operations.

Provides database operations for creating, retrieving, and managing reset tokens.
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.entities.password_reset import PasswordResetToken
from snackbase.infrastructure.persistence.models.password_reset import PasswordResetTokenModel


class PasswordResetRepository:
    """Repository for password reset token database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA-256.

        Args:
            token: The raw token string.

        Returns:
            SHA-256 hex digest of the token.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _to_model(self, entity: PasswordResetToken) -> PasswordResetTokenModel:
        """Convert domain entity to infrastructure model."""
        return PasswordResetTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            email=entity.email,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            created_at=entity.created_at,
        )

    def _to_entity(self, model: PasswordResetTokenModel) -> PasswordResetToken:
        """Convert infrastructure model to domain entity."""
        expires_at = model.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        created_at = model.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        used_at = model.used_at
        if used_at and used_at.tzinfo is None:
            used_at = used_at.replace(tzinfo=timezone.utc)

        return PasswordResetToken(
            id=model.id,
            user_id=model.user_id,
            email=model.email,
            token_hash=model.token_hash,
            expires_at=expires_at,
            created_at=created_at,
            used_at=used_at,
        )

    async def create(self, entity: PasswordResetToken) -> PasswordResetToken:
        """Store a new password reset token.

        Args:
            entity: The PasswordResetToken entity to store.

        Returns:
            The stored entity.
        """
        # Delete existing tokens for this user/email to avoid UNIQUE constraint violation
        # and invalidate old requests.
        await self.delete_for_user_email(entity.user_id, entity.email)

        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_token(self, token_plain: str) -> PasswordResetToken | None:
        """Look up a reset token by its plain text value.

        Args:
            token_plain: The raw token string.

        Returns:
            The PasswordResetToken entity if found, None otherwise.
        """
        token_hash = self._hash_token(token_plain)
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def mark_as_used(self, token_id: str) -> bool:
        """Mark a reset token as used.

        Args:
            token_id: The token's UUID.

        Returns:
            True if the token was updated, False if not found.
        """
        stmt = (
            update(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def delete_expired(self) -> int:
        """Delete all expired reset tokens.

        Returns:
            Number of tokens deleted.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.expires_at < now
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def get_active_for_user(self, user_id: str, email: str) -> PasswordResetToken | None:
        """Get an active (not expired, not used) token for a specific user and email.

        Args:
            user_id: The user's UUID.
            email: The email address.

        Returns:
            The PasswordResetToken entity if found, None otherwise.
        """
        now = datetime.now(timezone.utc)
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user_id,
            PasswordResetTokenModel.email == email,
            PasswordResetTokenModel.used_at == None,  # noqa: E711
            PasswordResetTokenModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete_for_user_email(self, user_id: str, email: str) -> int:
        """Delete all tokens for a specific user and email address.

        This is used to invalidate old requests and prevent UNIQUE constraint violations.

        Args:
            user_id: The user's UUID.
            email: The email address.

        Returns:
            Number of tokens deleted.
        """
        stmt = delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user_id,
            PasswordResetTokenModel.email == email,
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def delete_for_user(self, user_id: str) -> int:
        """Delete all tokens for a specific user.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of tokens deleted.
        """
        stmt = delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.rowcount
