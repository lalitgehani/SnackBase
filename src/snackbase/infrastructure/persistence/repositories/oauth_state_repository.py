"""OAuth state repository for database operations."""

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel


class OAuthStateRepository:
    """Repository for OAuth flow state database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, state: OAuthStateModel) -> OAuthStateModel:
        """Create a new OAuth state.

        Args:
            state: OAuth state model to create.

        Returns:
            Created OAuth state model.
        """
        self.session.add(state)
        await self.session.flush()
        return state

    async def get_by_id(self, state_id: str) -> Optional[OAuthStateModel]:
        """Get an OAuth state by ID.

        Args:
            state_id: OAuth state ID (UUID).

        Returns:
            OAuth state model if found, None otherwise.
        """
        result = await self.session.execute(
            select(OAuthStateModel).where(OAuthStateModel.id == state_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, state_token: str) -> Optional[OAuthStateModel]:
        """Get an OAuth state by its secure token.

        Args:
            state_token: Secure random state token.

        Returns:
            OAuth state model if found, None otherwise.
        """
        result = await self.session.execute(
            select(OAuthStateModel).where(OAuthStateModel.state_token == state_token)
        )
        return result.scalar_one_or_none()

    async def delete(self, state_id: str) -> bool:
        """Delete an OAuth state by ID.

        Args:
            state_id: OAuth state ID.

        Returns:
            True if deleted, False if not found.
        """
        state = await self.get_by_id(state_id)
        if not state:
            return False

        await self.session.delete(state)
        await self.session.flush()
        return True

    async def delete_expired(self, now: datetime) -> int:
        """Delete all expired OAuth states.

        Args:
            now: Current datetime to compare against expires_at.

        Returns:
            Number of deleted records.
        """
        stmt = sql_delete(OAuthStateModel).where(OAuthStateModel.expires_at <= now)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
