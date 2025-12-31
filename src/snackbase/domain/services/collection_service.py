"""Collection service for business logic.

Handles collection schema updates, validation, and deletion.
"""

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionValidationError, CollectionValidator
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.infrastructure.persistence.migration_service import MigrationService

logger = get_logger(__name__)


class CollectionService:
    """Service for collection business logic."""

    def __init__(
        self, 
        session: AsyncSession, 
        engine: AsyncEngine,
        migration_service: MigrationService | None = None
    ) -> None:
        """Initialize the service.

        Args:
            session: SQLAlchemy async session.
            engine: SQLAlchemy async engine.
            migration_service: Optional migration service.
        """
        self.session = session
        self.engine = engine
        self.repository = CollectionRepository(session)
        self.migration_service = migration_service or MigrationService(
            database_url=str(engine.url)
        )

    async def create_collection(
        self, name: str, schema: list[dict[str, Any]], user_id: str
    ) -> CollectionModel:
        """Create a new collection with migration.

        Args:
            name: Collection name.
            schema: List of field definitions.
            user_id: ID of the user creating the collection.

        Returns:
            The created collection model.

        Raises:
            CollectionValidationError: If validation fails.
            ValueError: If collection already exists.
        """
        # Validate name and schema
        validation_errors = CollectionValidator.validate(name, schema)
        if validation_errors:
            error_messages = [f"{e.field}: {e.message}" for e in validation_errors]
            raise ValueError(f"Validation failed: {'; '.join(error_messages)}")

        # Check uniqueness
        if await self.repository.name_exists(name):
            raise ValueError(f"Collection '{name}' already exists")

        # 1. Generate migration
        logger.info("Generating migration for new collection", collection_name=name)
        rev_id = self.migration_service.generate_create_collection_migration(name, schema)

        # 2. Apply migration
        logger.info("Applying migration", revision=rev_id)
        await self.migration_service.apply_migrations()

        # 3. Store collection record
        collection_id = str(uuid.uuid4())
        collection = CollectionModel(
            id=collection_id,
            name=name,
            schema=json.dumps(schema),
            migration_revision=rev_id
        )
        created_collection = await self.repository.create(collection)
        
        logger.info(
            "Collection created successfully with migration",
            collection_id=collection_id,
            collection_name=name,
            revision=rev_id,
            created_by=user_id,
        )

        return created_collection

    def validate_schema_update(
        self, existing_schema: list[dict[str, Any]], new_schema: list[dict[str, Any]]
    ) -> list[CollectionValidationError]:
        """Validate schema update changes."""
        errors: list[CollectionValidationError] = []

        # Create maps for easy lookup
        existing_fields = {field["name"]: field for field in existing_schema}
        new_fields = {field["name"]: field for field in new_schema}

        # Check for field deletions
        for field_name in existing_fields:
            if field_name not in new_fields:
                errors.append(
                    CollectionValidationError(
                        field=field_name,
                        message="Field deletion is not allowed for data safety",
                        code="field_deletion_not_allowed",
                    )
                )

        # Check for type changes in existing fields
        for field_name, existing_field in existing_fields.items():
            if field_name in new_fields:
                new_field = new_fields[field_name]
                if existing_field["type"] != new_field["type"]:
                    errors.append(
                        CollectionValidationError(
                            field=field_name,
                            message=f"Type change from '{existing_field['type']}' to '{new_field['type']}' is not allowed for data safety",
                            code="type_change_not_allowed",
                        )
                    )

        # Validate new fields
        new_field_names = set(new_fields.keys()) - set(existing_fields.keys())
        if new_field_names:
            new_field_list = [new_fields[name] for name in new_field_names]
            validation_errors = CollectionValidator.validate_schema(new_field_list)
            errors.extend(validation_errors)

        return errors

    async def update_collection_schema(
        self, collection_id: str, new_schema: list[dict[str, Any]]
    ) -> CollectionModel:
        """Update collection schema with migration.

        Args:
            collection_id: The collection ID.
            new_schema: The new schema.

        Returns:
            Updated collection model.
        """
        # Get existing collection
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        # Parse existing schema
        existing_schema = json.loads(collection.schema)

        # Validate schema update
        validation_errors = self.validate_schema_update(existing_schema, new_schema)
        if validation_errors:
            error_messages = [f"{e.field}: {e.message}" for e in validation_errors]
            raise ValueError(f"Schema validation failed: {'; '.join(error_messages)}")

        # Identify new fields
        existing_field_names = {field["name"] for field in existing_schema}
        new_fields = [
            field for field in new_schema if field["name"] not in existing_field_names
        ]

        # Generate and apply migration if new fields exist
        if new_fields:
            logger.info(
                "Generating migration for collection update",
                collection_id=collection_id,
                collection_name=collection.name,
                new_field_count=len(new_fields),
            )
            rev_id = self.migration_service.generate_update_collection_migration(
                collection.name, new_fields
            )
            
            logger.info("Applying migration", revision=rev_id)
            await self.migration_service.apply_migrations()
            
            # Update revision in model
            collection.migration_revision = rev_id

        # Update collection schema in database
        collection.schema = json.dumps(new_schema)
        updated_collection = await self.repository.update(collection)

        logger.info(
            "Collection schema updated successfully",
            collection_id=collection_id,
            collection_name=collection.name,
        )

        return updated_collection

    async def delete_collection(self, collection_id: str) -> dict[str, Any]:
        """Delete collection with migration.

        Args:
            collection_id: The collection ID.

        Returns:
            Dictionary with deletion confirmation.
        """
        # Get collection
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        # Get record count for confirmation
        table_name = TableBuilder.generate_table_name(collection.name)
        record_count = await self.repository.get_record_count(table_name)

        logger.info(
            "Generating migration for collection deletion",
            collection_id=collection_id,
            collection_name=collection.name,
        )

        # 1. Generate migration
        rev_id = self.migration_service.generate_delete_collection_migration(collection.name)

        # 2. Apply migration
        logger.info("Applying migration", revision=rev_id)
        await self.migration_service.apply_migrations()

        # 3. Delete collection from database
        await self.repository.delete(collection)

        logger.info(
            "Collection deleted successfully",
            collection_id=collection_id,
            collection_name=collection.name,
            records_deleted=record_count,
            revision=rev_id
        )

        return {
            "collection_id": collection_id,
            "collection_name": collection.name,
            "table_name": table_name,
            "records_deleted": record_count,
            "migration_revision": rev_id
        }

    async def get_record_count(self, collection_id: str) -> int:
        """Get count of records in a collection."""
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        table_name = TableBuilder.generate_table_name(collection.name)
        return await self.repository.get_record_count(table_name)
