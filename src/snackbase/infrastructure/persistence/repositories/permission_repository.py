"""Permission repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import PermissionModel


class PermissionRepository:
    """Repository for permission database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, permission: PermissionModel) -> PermissionModel:
        """Create a new permission.

        Args:
            permission: Permission model to create.

        Returns:
            Created permission model.
        """
        self.session.add(permission)
        await self.session.flush()
        return permission

    async def get_by_id(self, permission_id: int) -> PermissionModel | None:
        """Get a permission by ID.

        Args:
            permission_id: Permission ID.

        Returns:
            Permission model if found, None otherwise.
        """
        result = await self.session.execute(
            select(PermissionModel).where(PermissionModel.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_role_id(self, role_id: int) -> list[PermissionModel]:
        """Get all permissions for a role.

        Args:
            role_id: Role ID.

        Returns:
            List of permission models for the role.
        """
        result = await self.session.execute(
            select(PermissionModel).where(PermissionModel.role_id == role_id)
        )
        return list(result.scalars().all())

    async def get_by_collection(self, collection: str) -> list[PermissionModel]:
        """Get all permissions for a collection.

        Also includes permissions for "*" (all collections).

        Args:
            collection: Collection name.

        Returns:
            List of permission models for the collection.
        """
        result = await self.session.execute(
            select(PermissionModel).where(
                (PermissionModel.collection == collection)
                | (PermissionModel.collection == "*")
            )
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[PermissionModel]:
        """List all permissions.

        Returns:
            List of all permission models.
        """
        result = await self.session.execute(
            select(PermissionModel).order_by(PermissionModel.id)
        )
        return list(result.scalars().all())

    async def delete(self, permission_id: int) -> bool:
        """Delete a permission by ID.

        Args:
            permission_id: Permission ID.

        Returns:
            True if deleted, False if not found.
        """
        permission = await self.get_by_id(permission_id)
        if permission is None:
            return False
        await self.session.delete(permission)
        await self.session.flush()
        return True

    async def exists_for_role_and_collection(
        self, role_id: int, collection: str
    ) -> bool:
        """Check if a permission exists for a role and collection.

        Args:
            role_id: Role ID.
            collection: Collection name.

        Returns:
            True if permission exists, False otherwise.
        """
        result = await self.session.execute(
            select(PermissionModel.id).where(
                PermissionModel.role_id == role_id,
                PermissionModel.collection == collection,
            )
        )
        return result.scalar_one_or_none() is not None

    async def find_permissions_using_macro(self, macro_name: str) -> list[PermissionModel]:
        """Find all permissions that use a specific macro.

        Args:
            macro_name: The macro name (with or without @ prefix).

        Returns:
            List of permissions that reference the macro in their rules.
        """
        import json

        # Normalize macro name (ensure it has @ prefix for search)
        search_name = macro_name if macro_name.startswith("@") else f"@{macro_name}"

        # Get all permissions
        all_permissions = await self.list_all()

        # Filter permissions that use the macro
        using_macro = []
        for permission in all_permissions:
            try:
                rules = json.loads(permission.rules)
                # Check each operation's rule expression
                for operation in ["create", "read", "update", "delete"]:
                    if operation in rules and isinstance(rules[operation], dict):
                        rule_expr = rules[operation].get("rule", "")
                        if search_name in rule_expr:
                            using_macro.append(permission)
                            break  # Found usage, no need to check other operations
            except (json.JSONDecodeError, TypeError):
                # Skip invalid rules
                continue

        return using_macro
