"""Repository for group database operations."""

from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snackbase.domain.services.permission_cache import PermissionCache
from snackbase.infrastructure.persistence.models import GroupModel, UserModel, UsersGroupsModel
from snackbase.infrastructure.persistence.models.users_groups import UsersGroupsModel


class GroupRepository:
    """Repository for group database operations."""

    def __init__(self, session: AsyncSession, permission_cache: PermissionCache | None = None) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
            permission_cache: Optional permission cache for invalidation.
        """
        self.session = session
        self.permission_cache = permission_cache

    async def create(self, group: GroupModel) -> GroupModel:
        """Create a new group.

        Args:
            group: Group model to create.

        Returns:
            Created group model.
        """
        self.session.add(group)
        await self.session.flush()
        return group

    async def get_by_id(self, group_id: str) -> GroupModel | None:
        """Get a group by ID.

        Args:
            group_id: Group ID.

        Returns:
            Group model if found, None otherwise.
        """
        result = await self.session.execute(
            select(GroupModel).where(GroupModel.id == group_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_account(self, name: str, account_id: str) -> GroupModel | None:
        """Get a group by name and account.

        Args:
            name: Group name.
            account_id: Account ID.

        Returns:
            Group model if found, None otherwise.
        """
        result = await self.session.execute(
            select(GroupModel).where(
                (GroupModel.name == name) & (GroupModel.account_id == account_id)
            )
        )
        return result.scalar_one_or_none()

    async def list(self, account_id: str, skip: int = 0, limit: int = 100) -> list[GroupModel]:
        """List groups for an account.

        Args:
            account_id: Account ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of group models.
        """
        result = await self.session.execute(
            select(GroupModel)
            .where(GroupModel.account_id == account_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[GroupModel]:
        """List all groups across all accounts (for superadmins).

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of group models.
        """
        result = await self.session.execute(
            select(GroupModel)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, group: GroupModel) -> GroupModel:
        """Update a group.

        Args:
            group: Group model to update.

        Returns:
            Updated group model.
        """
        # Ensure attached to session
        if group not in self.session:
            self.session.add(group)
        
        await self.session.flush()
        return group

    async def delete(self, group: GroupModel) -> None:
        """Delete a group.

        Args:
            group: Group model to delete.
        """
        await self.session.delete(group)
        await self.session.flush()

    async def add_user(self, group_id: str, user_id: str) -> None:
        """Add a user to a group.

        Args:
            group_id: Group ID.
            user_id: User ID.
        """
        # Create junction record
        user_group = UsersGroupsModel(user_id=user_id, group_id=group_id)
        self.session.add(user_group)
        await self.session.flush()
        
        # Invalidate cache if available
        if self.permission_cache:
            self.permission_cache.invalidate_user(user_id)

    async def remove_user(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group.

        Args:
            group_id: Group ID.
            user_id: User ID.
        """
        await self.session.execute(
            delete(UsersGroupsModel).where(
                (UsersGroupsModel.group_id == group_id) & 
                (UsersGroupsModel.user_id == user_id)
            )
        )
        await self.session.flush()
        
        # Invalidate cache if available
        if self.permission_cache:
            self.permission_cache.invalidate_user(user_id)
            
    async def is_user_in_group(self, group_id: str, user_id: str) -> bool:
        """Check if a user is in a group.
        
        Args:
            group_id: Group ID.
            user_id: User ID.
            
        Returns:
            True if user is in group, False otherwise.
        """
        result = await self.session.execute(
            select(UsersGroupsModel).where(
                (UsersGroupsModel.group_id == group_id) & 
                (UsersGroupsModel.user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None
