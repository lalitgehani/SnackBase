"""Collection service for business logic.

Handles collection schema updates, validation, and deletion.
"""

import json
import uuid
from datetime import UTC
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionValidationError, CollectionValidator
from snackbase.infrastructure.persistence.migration_service import MigrationService
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


class CollectionService:
    """Service for collection business logic."""

    def __init__(
        self,
        session: AsyncSession,
        engine: AsyncEngine,
        migration_service: MigrationService | None = None,
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
        self.migration_service = migration_service or MigrationService(engine=engine)

    async def create_collection(
        self,
        name: str,
        schema: list[dict[str, Any]],
        user_id: str,
        rules_data: dict[str, Any] | None = None,
    ) -> CollectionModel:
        """Create a new collection with schema and optional rules.

        Args:
            name: Collection name.
            schema: List of field definitions.
            user_id: ID of the user creating the collection.
            rules_data: Optional dictionary containing rules for the collection.

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
            id=collection_id, name=name, schema=json.dumps(schema), migration_revision=rev_id
        )
        created_collection = await self.repository.create(collection)

        # 4. Create collection rules
        from snackbase.infrastructure.persistence.models.collection_rule import CollectionRuleModel
        from snackbase.infrastructure.persistence.repositories.collection_rule_repository import (
            CollectionRuleRepository,
        )

        rule_repo = CollectionRuleRepository(self.session)

        # Default rules (locked) if none provided
        rules_dict = rules_data or {}

        rule = CollectionRuleModel(
            id=str(uuid.uuid4()),
            collection_id=collection_id,
            list_rule=rules_dict.get("list_rule"),
            view_rule=rules_dict.get("view_rule"),
            create_rule=rules_dict.get("create_rule"),
            update_rule=rules_dict.get("update_rule"),
            delete_rule=rules_dict.get("delete_rule"),
            list_fields=rules_dict.get("list_fields", "*"),
            view_fields=rules_dict.get("view_fields", "*"),
            create_fields=rules_dict.get("create_fields", "*"),
            update_fields=rules_dict.get("update_fields", "*"),
        )
        await rule_repo.create(rule)

        logger.info(
            "Collection created successfully with rules and migration",
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

        # Validate the entire new schema (not just new fields)
        # This catches duplicate field names and other schema-wide validation issues
        validation_errors = CollectionValidator.validate_schema(new_schema)
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
        new_fields = [field for field in new_schema if field["name"] not in existing_field_names]

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
            revision=rev_id,
        )

        return {
            "collection_id": collection_id,
            "collection_name": collection.name,
            "table_name": table_name,
            "records_deleted": record_count,
            "migration_revision": rev_id,
        }

    async def get_record_count(self, collection_id: str) -> int:
        """Get count of records in a collection."""
        collection = await self.repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found")

        table_name = TableBuilder.generate_table_name(collection.name)
        return await self.repository.get_record_count(table_name)

    async def export_collections(
        self,
        user_email: str,
        collection_ids: list[str] | None = None,
    ) -> tuple[bytes, str]:
        """Export collections to JSON format.

        Args:
            user_email: Email of the user performing the export.
            collection_ids: Optional list of collection IDs to export. If None, exports all.

        Returns:
            Tuple of (JSON bytes, media type).
        """
        from datetime import datetime

        from snackbase.infrastructure.persistence.repositories.collection_rule_repository import (
            CollectionRuleRepository,
        )

        # Fetch collections
        if collection_ids:
            collections = []
            for cid in collection_ids:
                collection = await self.repository.get_by_id(cid)
                if collection:
                    collections.append(collection)
        else:
            collections = await self.repository.list_all()

        # Build export data
        rule_repo = CollectionRuleRepository(self.session)
        export_collections = []

        for collection in collections:
            # Parse schema
            schema = json.loads(collection.schema)

            # Get rules
            rule = await rule_repo.get_by_collection_id(collection.id)
            rules_dict = {
                "list_rule": rule.list_rule if rule else None,
                "view_rule": rule.view_rule if rule else None,
                "create_rule": rule.create_rule if rule else None,
                "update_rule": rule.update_rule if rule else None,
                "delete_rule": rule.delete_rule if rule else None,
                "list_fields": rule.list_fields if rule else "*",
                "view_fields": rule.view_fields if rule else "*",
                "create_fields": rule.create_fields if rule else "*",
                "update_fields": rule.update_fields if rule else "*",
            }

            export_collections.append(
                {
                    "name": collection.name,
                    "schema": schema,
                    "rules": rules_dict,
                }
            )

        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "exported_by": user_email,
            "collections": export_collections,
        }

        logger.info(
            "Exported collections",
            collection_count=len(export_collections),
            exported_by=user_email,
        )

        return json.dumps(export_data, indent=2).encode("utf-8"), "application/json"

    async def import_collections(
        self,
        export_data: dict[str, Any],
        strategy: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Import collections from export data.

        Migrations are always generated to ensure database tables are created.

        Args:
            export_data: The parsed export JSON data.
            strategy: Import strategy - "error", "skip", or "update".
            user_id: ID of the user performing the import.

        Returns:
            Dictionary with import results.
        """
        # Validate version
        version = export_data.get("version", "")
        if not version.startswith("1."):
            raise ValueError(f"Unsupported export version: {version}")

        collections_data = export_data.get("collections", [])

        # Sort collections by dependency (reference fields should come after their targets)
        sorted_collections = self._sort_collections_by_dependency(collections_data)

        results: list[dict[str, str]] = []
        migrations_created: list[str] = []
        imported_count = 0
        skipped_count = 0
        updated_count = 0
        failed_count = 0

        for coll_data in sorted_collections:
            name = coll_data.get("name", "")
            schema = coll_data.get("schema", [])
            rules = coll_data.get("rules", {})

            try:
                # Check if collection exists
                existing = await self.repository.get_by_name(name)

                if existing:
                    if strategy == "error":
                        raise ValueError(f"Collection '{name}' already exists")
                    elif strategy == "skip":
                        results.append(
                            {
                                "name": name,
                                "status": "skipped",
                                "message": "Collection already exists",
                            }
                        )
                        skipped_count += 1
                        continue
                    elif strategy == "update":
                        # Update existing collection schema
                        try:
                            await self.update_collection_schema(existing.id, schema)
                            results.append(
                                {
                                    "name": name,
                                    "status": "updated",
                                    "message": "Collection schema updated",
                                }
                            )
                            updated_count += 1
                            continue
                        except ValueError as e:
                            results.append(
                                {
                                    "name": name,
                                    "status": "error",
                                    "message": str(e),
                                }
                            )
                            failed_count += 1
                            continue

                # Create new collection with migration
                collection = await self.create_collection(
                    name=name,
                    schema=schema,
                    user_id=user_id,
                    rules_data=rules,
                )
                if collection.migration_revision:
                    migrations_created.append(collection.migration_revision)

                results.append(
                    {
                        "name": name,
                        "status": "imported",
                        "message": "Collection created successfully",
                    }
                )
                imported_count += 1

            except Exception as e:
                logger.error(
                    "Failed to import collection",
                    collection_name=name,
                    error=str(e),
                )
                results.append(
                    {
                        "name": name,
                        "status": "error",
                        "message": str(e),
                    }
                )
                failed_count += 1

        logger.info(
            "Import completed",
            imported=imported_count,
            skipped=skipped_count,
            updated=updated_count,
            failed=failed_count,
        )

        return {
            "success": failed_count == 0,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "collections": results,
            "migrations_created": migrations_created,
        }

    def _sort_collections_by_dependency(
        self, collections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Sort collections so that referenced collections come before those that reference them.

        Args:
            collections: List of collection data dictionaries.

        Returns:
            Sorted list of collections.
        """
        # Build dependency graph
        name_to_collection = {c["name"]: c for c in collections}
        dependencies: dict[str, set[str]] = {}

        for coll in collections:
            name = coll["name"]
            deps = set()
            for field in coll.get("schema", []):
                if field.get("type") == "reference":
                    target = field.get("collection")
                    if target and target in name_to_collection and target != name:
                        deps.add(target)
            dependencies[name] = deps

        # Topological sort
        sorted_names: list[str] = []
        visited: set[str] = set()
        temp_visited: set[str] = set()

        def visit(name: str) -> None:
            if name in temp_visited:
                # Circular dependency detected - just continue
                logger.warning("Circular dependency detected", collection=name)
                return
            if name in visited:
                return
            temp_visited.add(name)
            for dep in dependencies.get(name, set()):
                visit(dep)
            temp_visited.remove(name)
            visited.add(name)
            sorted_names.append(name)

        for name in dependencies:
            if name not in visited:
                visit(name)

        return [name_to_collection[name] for name in sorted_names]
