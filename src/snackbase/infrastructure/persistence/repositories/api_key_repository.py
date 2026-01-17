"""Repository for API key database operations."""

from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.api_key import APIKeyModel


class APIKeyRepository:
    """Repository for API key database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, api_key: APIKeyModel) -> APIKeyModel:
        """Create a new API key.

        Args:
            api_key: APIKey model to create.

        Returns:
            Created APIKey model.
        """
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get_by_id(self, key_id: str) -> APIKeyModel | None:
        """Get an API key by ID.

        Args:
            key_id: API key ID (UUID string).

        Returns:
            APIKey model if found, None otherwise.
        """
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> APIKeyModel | None:
        """Get an API key by its hash.

        Args:
            key_hash: SHA-256 hash of the API key.

        Returns:
            APIKey model if found, None otherwise.
        """
        result = await self.session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.key_hash == key_hash,
                    APIKeyModel.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> Sequence[APIKeyModel]:
        """List all active API keys for a specific user.

        Args:
            user_id: User ID to filter by.

        Returns:
            List of active API keys.
        """
        result = await self.session.execute(
            select(APIKeyModel)
            .where(
                and_(
                    APIKeyModel.user_id == user_id,
                    APIKeyModel.is_active == True,
                )
            )
            .order_by(APIKeyModel.created_at.desc())
        )
        return result.scalars().all()

    async def list_all_by_user(self, user_id: str) -> Sequence[APIKeyModel]:
        """List all API keys (including revoked) for a specific user.

        Args:
            user_id: User ID to filter by.

        Returns:
            List of all API keys for the user.
        """
        result = await self.session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.user_id == user_id)
            .order_by(APIKeyModel.created_at.desc())
        )
        return result.scalars().all()

    async def update_last_used(self, key_id: str) -> None:
        """Update the last_used_at timestamp for an API key.

        Args:
            key_id: ID of the key to update.
        """
        await self.session.execute(
            update(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .values(last_used_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def soft_delete(self, key_id: str) -> bool:
        """Soft delete (revoke) an API key.

        Args:
            key_id: ID of the key to revoke.

        Returns:
            True if revoked, False if not found.
        """
        result = await self.session.execute(
            update(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .values(is_active=False)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def count_by_user(self, user_id: str) -> int:
        """Count active API keys for a specific user.

        Args:
            user_id: User ID to filter by.

        Returns:
            Number of active API keys.
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(APIKeyModel.id)).where(
                and_(
                    APIKeyModel.user_id == user_id,
                    APIKeyModel.is_active == True,
                )
            )
        )
        return result.scalar_one() or 0
