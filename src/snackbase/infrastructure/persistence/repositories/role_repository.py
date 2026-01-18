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

    async def create(self, role: RoleModel) -> RoleModel:
        """Create a new role.

        Args:
            role: Role model to create.

        Returns:
            Created role model.
        """
        self.session.add(role)
        await self.session.flush()
        return role

    async def delete(self, role_id: int) -> bool:
        """Delete a role by ID.

        Args:
            role_id: Role ID.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result.scalar_one_or_none()
        if not role:
            return False

        await self.session.delete(role)
        await self.session.flush()
        return True

    async def list_all(self) -> list[RoleModel]:
        """Get all roles.

        Returns:
            List of all role models.
        """
        result = await self.session.execute(select(RoleModel))
        return list(result.scalars().all())

    async def update(self, role_id: int, name: str, description: str | None) -> RoleModel | None:
        """Update a role.

        Args:
            role_id: Role ID.
            name: New role name.
            description: New role description.

        Returns:
            Updated role model if found, None otherwise.
        """
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result.scalar_one_or_none()
        if not role:
            return None

        role.name = name
        role.description = description
        await self.session.flush()
        return role


