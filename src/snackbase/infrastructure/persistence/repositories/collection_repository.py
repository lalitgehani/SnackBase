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

    async def count_all(self) -> int:
        """Count total number of collections.

        Returns:
            Total count of collections.
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(CollectionModel.id)))
        return result.scalar_one() or 0

    async def list_all(self) -> list[CollectionModel]:
        """Get all collections without pagination.

        Returns:
            List of all collection models.
        """
        result = await self.session.execute(
            select(CollectionModel).order_by(CollectionModel.name)
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[CollectionModel], int]:
        """Get all collections with pagination and search.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Field to sort by.
            sort_order: Sort order ('asc' or 'desc').
            search: Optional search term for name or ID.

        Returns:
            Tuple of (list of collections, total count).
        """
        from sqlalchemy import func, or_

        # Build base query
        query = select(CollectionModel)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    CollectionModel.name.ilike(search_pattern),
                    CollectionModel.id.ilike(search_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one() or 0

        # Apply sorting
        sort_column = getattr(CollectionModel, sort_by, CollectionModel.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        collections = list(result.scalars().all())

        return collections, total

    async def update(self, collection: CollectionModel) -> CollectionModel:
        """Update a collection.

        Args:
            collection: The collection model to update.

        Returns:
            The updated collection model.
        """
        await self.session.flush()
        await self.session.refresh(collection)
        return collection

    async def delete(self, collection: CollectionModel) -> None:
        """Delete a collection.

        Args:
            collection: The collection model to delete.
        """
        await self.session.delete(collection)
        await self.session.flush()

    async def get_record_count(self, table_name: str) -> int:
        """Get the count of records in a collection table.

        Args:
            table_name: The physical table name.

        Returns:
            Number of records in the table.
        """
        from sqlalchemy import text

        # Use raw SQL to count records in the dynamic table
        query = text(f"SELECT COUNT(*) FROM {table_name}")
        result = await self.session.execute(query)
        return result.scalar_one() or 0

