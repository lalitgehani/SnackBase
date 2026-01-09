"""Repository for email verification token operations.

Provides database operations for creating, retrieving, and managing verification tokens.
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.entities.email_verification import EmailVerificationToken
from snackbase.infrastructure.persistence.models.email_verification import EmailVerificationTokenModel


class EmailVerificationRepository:
    """Repository for email verification token database operations."""

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

    def _to_model(self, entity: EmailVerificationToken) -> EmailVerificationTokenModel:
        """Convert domain entity to infrastructure model."""
        return EmailVerificationTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            email=entity.email,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            created_at=entity.created_at,
        )

    def _to_entity(self, model: EmailVerificationTokenModel) -> EmailVerificationToken:
        """Convert infrastructure model to domain entity."""
        return EmailVerificationToken(
            id=model.id,
            user_id=model.user_id,
            email=model.email,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            created_at=model.created_at,
            used_at=model.used_at,
        )

    async def create(self, entity: EmailVerificationToken) -> EmailVerificationToken:
        """Store a new email verification token.

        Args:
            entity: The EmailVerificationToken entity to store.

        Returns:
            The stored entity.
        """
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_token(self, token_plain: str) -> EmailVerificationToken | None:
        """Look up a verification token by its plain text value.

        Args:
            token_plain: The raw token string.

        Returns:
            The EmailVerificationToken entity if found, None otherwise.
        """
        token_hash = self._hash_token(token_plain)
        stmt = select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def mark_as_used(self, token_id: str) -> bool:
        """Mark a verification token as used.

        Args:
            token_id: The token's UUID.

        Returns:
            True if the token was updated, False if not found.
        """
        stmt = (
            update(EmailVerificationTokenModel)
            .where(EmailVerificationTokenModel.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def delete_expired(self) -> int:
        """Delete all expired verification tokens.

        Returns:
            Number of tokens deleted.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.expires_at < now
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def get_active_for_user(self, user_id: str, email: str) -> EmailVerificationToken | None:
        """Get an active (not expired, not used) token for a specific user and email.

        Args:
            user_id: The user's UUID.
            email: The email address.

        Returns:
            The EmailVerificationToken entity if found, None otherwise.
        """
        now = datetime.now(timezone.utc)
        stmt = select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.user_id == user_id,
            EmailVerificationTokenModel.email == email,
            EmailVerificationTokenModel.used_at == None,  # noqa: E711
            EmailVerificationTokenModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
