"""Repository for collection rule operations.

Provides CRUD operations for the collection_rules table.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import CollectionModel, CollectionRuleModel


class CollectionRuleRepository:
    """Repository for collection rule database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, rule: CollectionRuleModel) -> CollectionRuleModel:
        """Create a new collection rule.

        Args:
            rule: The collection rule model to create.

        Returns:
            The created collection rule model.
        """
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def get_by_collection_id(self, collection_id: str) -> CollectionRuleModel | None:
        """Get collection rules by collection ID.

        Args:
            collection_id: The collection ID.

        Returns:
            The collection rule model if found, None otherwise.
        """
        result = await self.session.execute(
            select(CollectionRuleModel).where(
                CollectionRuleModel.collection_id == collection_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_collection_name(self, collection_name: str) -> CollectionRuleModel | None:
        """Get collection rules by collection name.

        Joins with the collections table to find rules by collection name.

        Args:
            collection_name: The collection name.

        Returns:
            The collection rule model if found, None otherwise.
        """
        result = await self.session.execute(
            select(CollectionRuleModel)
            .join(CollectionModel, CollectionRuleModel.collection_id == CollectionModel.id)
            .where(CollectionModel.name == collection_name)
        )
        return result.scalar_one_or_none()

    async def update(self, rule: CollectionRuleModel) -> CollectionRuleModel:
        """Update a collection rule.

        Args:
            rule: The collection rule model to update.

        Returns:
            The updated collection rule model.
        """
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete(self, rule: CollectionRuleModel) -> None:
        """Delete a collection rule.

        Args:
            rule: The collection rule model to delete.
        """
        await self.session.delete(rule)
        await self.session.flush()
