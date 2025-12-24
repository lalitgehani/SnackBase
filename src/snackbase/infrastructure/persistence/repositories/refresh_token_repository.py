"""Repository for refresh token operations.

Provides database operations for storing and managing refresh tokens.
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import RefreshTokenModel


class RefreshTokenRepository:
    """Repository for refresh token database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token using SHA-256.

        Args:
            token: The raw JWT token string.

        Returns:
            SHA-256 hex digest of the token.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, model: RefreshTokenModel) -> RefreshTokenModel:
        """Store a new refresh token.

        Args:
            model: The RefreshTokenModel to store.

        Returns:
            The stored model with updated fields.
        """
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_hash(self, token: str) -> RefreshTokenModel | None:
        """Look up a refresh token by its hash.

        Args:
            token: The raw JWT token string.

        Returns:
            The RefreshTokenModel if found, None otherwise.
        """
        token_hash = self.hash_token(token)
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: str) -> bool:
        """Revoke a refresh token by ID.

        Args:
            token_id: The token's UUID.

        Returns:
            True if a token was revoked, False if not found.
        """
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(is_revoked=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str, account_id: str) -> int:
        """Revoke all refresh tokens for a user in an account.

        Args:
            user_id: The user's UUID.
            account_id: The account ID.

        Returns:
            Number of tokens revoked.
        """
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.account_id == account_id,
                RefreshTokenModel.is_revoked == False,  # noqa: E712
            )
            .values(is_revoked=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def is_valid(self, token: str) -> bool:
        """Check if a refresh token is valid (not revoked and not expired).

        Args:
            token: The raw JWT token string.

        Returns:
            True if the token is valid, False otherwise.
        """
        token_model = await self.get_by_hash(token)
        if token_model is None:
            return False
        if token_model.is_revoked:
            return False
        if token_model.expires_at < datetime.now(timezone.utc):
            return False
        return True
