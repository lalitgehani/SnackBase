"""Collection service for business logic.

Handles collection schema updates, validation, and deletion.
"""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionValidationError, CollectionValidator
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


class CollectionService:
    """Service for collection business logic."""

    def __init__(self, session: AsyncSession, engine: AsyncEngine) -> None:
        """Initialize the service.

        Args:
            session: SQLAlchemy async session.
            engine: SQLAlchemy async engine.
        """
        self.session = session
        self.engine = engine
        self.repository = CollectionRepository(session)

    def validate_schema_update(
        self, existing_schema: list[dict[str, Any]], new_schema: list[dict[str, Any]]
    ) -> list[CollectionValidationError]:
        """Validate schema update changes.

        Ensures:
        - No type changes to existing fields
        - No field deletions
        - New fields are valid

        Args:
            existing_schema: Current schema.
            new_schema: Proposed new schema.

        Returns:
            List of validation errors (empty if valid).
        """
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
            # Use CollectionValidator to validate new fields
            # We create a temporary collection name for validation
            validation_errors = CollectionValidator.validate_schema(new_field_list)
            errors.extend(validation_errors)

        return errors

    async def update_collection_schema(
        self, collection_id: str, new_schema: list[dict[str, Any]]
    ) -> CollectionModel:
        """Update collection schema with table alteration.

        Args:
            collection_id: The collection ID.
            new_schema: The new schema.

        Returns:
            Updated collection model.

        Raises:
            ValueError: If validation fails or collection not found.
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
            error_messages = [
                f"{e.field}: {e.message}" for e in validation_errors
            ]
            raise ValueError(f"Schema validation failed: {'; '.join(error_messages)}")

        # Identify new fields
        existing_field_names = {field["name"] for field in existing_schema}
        new_fields = [
            field for field in new_schema if field["name"] not in existing_field_names
        ]

        # Add new columns to table if any
        if new_fields:
            logger.info(
                "Adding new columns to collection table",
                collection_id=collection_id,
                collection_name=collection.name,
                new_field_count=len(new_fields),
            )
            await TableBuilder.add_columns(self.engine, collection.name, new_fields)

        # Update collection schema in database
        collection.schema = json.dumps(new_schema)
        updated_collection = await self.repository.update(collection)

        logger.info(
            "Collection schema updated successfully",
            collection_id=collection_id,
            collection_name=collection.name,
            new_field_count=len(new_fields),
        )

        return updated_collection

    async def delete_collection(self, collection_id: str) -> dict[str, Any]:
        """Delete collection and its table.

        Args:
            collection_id: The collection ID.

        Returns:
            Dictionary with deletion confirmation and record count.

        Raises:
            ValueError: If collection not found.
        """
        # Get collection
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        # Get record count for confirmation
        table_name = TableBuilder.generate_table_name(collection.name)
        record_count = await self.repository.get_record_count(table_name)

        logger.info(
            "Deleting collection and table",
            collection_id=collection_id,
            collection_name=collection.name,
            table_name=table_name,
            record_count=record_count,
        )

        # Drop the physical table
        await TableBuilder.drop_table(self.engine, collection.name)

        # Delete collection from database
        await self.repository.delete(collection)
        await self.session.commit()

        logger.info(
            "Collection deleted successfully",
            collection_id=collection_id,
            collection_name=collection.name,
            records_deleted=record_count,
        )

        return {
            "collection_id": collection_id,
            "collection_name": collection.name,
            "table_name": table_name,
            "records_deleted": record_count,
        }

    async def get_record_count(self, collection_id: str) -> int:
        """Get count of records in a collection.

        Args:
            collection_id: The collection ID.

        Returns:
            Number of records.

        Raises:
            ValueError: If collection not found.
        """
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        table_name = TableBuilder.generate_table_name(collection.name)
        return await self.repository.get_record_count(table_name)
