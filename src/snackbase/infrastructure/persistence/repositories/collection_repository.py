"""Repository for collection operations.

Provides CRUD operations for the collections table.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import CollectionModel


class CollectionRepository:
    """Repository for collection database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, collection: CollectionModel) -> CollectionModel:
        """Create a new collection.

        Args:
            collection: The collection model to create.

        Returns:
            The created collection model.
        """
        self.session.add(collection)
        await self.session.flush()
        return collection

    async def get_by_name(self, name: str) -> CollectionModel | None:
        """Get a collection by name.

        Args:
            name: The collection name.

        Returns:
            The collection model if found, None otherwise.
        """
        result = await self.session.execute(
            select(CollectionModel).where(CollectionModel.name == name)
        )
        return result.scalar_one_or_none()

    async def name_exists(self, name: str) -> bool:
        """Check if a collection with the given name exists.

        Args:
            name: The collection name to check.

        Returns:
            True if the name exists, False otherwise.
        """
        result = await self.session.execute(
            select(CollectionModel.id).where(CollectionModel.name == name).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, collection_id: str) -> CollectionModel | None:
        """Get a collection by ID.

        Args:
            collection_id: The collection ID.

        Returns:
            The collection model if found, None otherwise.
        """
        result = await self.session.execute(
            select(CollectionModel).where(CollectionModel.id == collection_id)
        )
        return result.scalar_one_or_none()
