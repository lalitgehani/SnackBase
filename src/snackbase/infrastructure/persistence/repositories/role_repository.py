"""Role repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import RoleModel


class RoleRepository:
    """Repository for role database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def get_by_id(self, role_id: int) -> RoleModel | None:
        """Get a role by ID.

        Args:
            role_id: Role ID.

        Returns:
            Role model if found, None otherwise.
        """
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> RoleModel | None:
        """Get a role by name.

        Args:
            name: Role name (e.g., 'admin', 'user').

        Returns:
            Role model if found, None otherwise.
        """
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.name == name)
        )
        return result.scalar_one_or_none()
