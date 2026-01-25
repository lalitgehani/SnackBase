"""Unit tests for Collection Export/Import functionality."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.domain.services import CollectionService
from snackbase.infrastructure.persistence.models import CollectionModel


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_engine():
    """Create a mock database engine."""
    return MagicMock()


@pytest.fixture
def mock_migration_service():
    """Create a mock migration service."""
    service = MagicMock()
    service.generate_create_collection_migration.return_value = "rev1"
    service.generate_update_collection_migration.return_value = "rev2"
    service.generate_delete_collection_migration.return_value = "rev3"
    service.apply_migrations = AsyncMock()
    return service


@pytest.fixture
def collection_service(mock_session, mock_engine, mock_migration_service):
    """Create a CollectionService instance."""
    return CollectionService(mock_session, mock_engine, migration_service=mock_migration_service)


@pytest.fixture
def sample_schema():
    """Sample collection schema."""
    return [
        {"name": "title", "type": "text", "required": True},
        {"name": "count", "type": "number", "default": 0},
    ]


@pytest.fixture
def sample_collection(sample_schema):
    """Sample collection model."""
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(sample_schema),
        migration_revision="rev1",
    )
    return collection


@pytest.fixture
def sample_rule():
    """Sample collection rule model."""
    rule = MagicMock()
    rule.list_rule = ""
    rule.view_rule = ""
    rule.create_rule = None
    rule.update_rule = None
    rule.delete_rule = None
    rule.list_fields = "*"
    rule.view_fields = "*"
    rule.create_fields = "*"
    rule.update_fields = "*"
    return rule


@pytest.mark.asyncio
class TestExportCollections:
    """Tests for export_collections method."""

    async def test_export_all_collections(
        self, collection_service, sample_collection, sample_rule
    ):
        """Test exporting all collections."""
        # Mock repository
        collection_service.repository.list_all = AsyncMock(return_value=[sample_collection])

        # Mock rule repository
        with patch(
            "snackbase.infrastructure.persistence.repositories.collection_rule_repository.CollectionRuleRepository"
        ) as MockRuleRepo:
            mock_rule_repo = MagicMock()
            mock_rule_repo.get_by_collection_id = AsyncMock(return_value=sample_rule)
            MockRuleRepo.return_value = mock_rule_repo

            # Export
            content, media_type = await collection_service.export_collections(
                user_email="admin@example.com"
            )

            # Verify
            assert media_type == "application/json"
            data = json.loads(content.decode("utf-8"))
            assert data["version"] == "1.0"
            assert data["exported_by"] == "admin@example.com"
            assert len(data["collections"]) == 1
            assert data["collections"][0]["name"] == "TestCollection"
            assert len(data["collections"][0]["schema"]) == 2

    async def test_export_specific_collections(
        self, collection_service, sample_collection, sample_rule
    ):
        """Test exporting specific collections by ID."""
        # Mock repository
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)

        # Mock rule repository
        with patch(
            "snackbase.infrastructure.persistence.repositories.collection_rule_repository.CollectionRuleRepository"
        ) as MockRuleRepo:
            mock_rule_repo = MagicMock()
            mock_rule_repo.get_by_collection_id = AsyncMock(return_value=sample_rule)
            MockRuleRepo.return_value = mock_rule_repo

            # Export
            content, media_type = await collection_service.export_collections(
                user_email="admin@example.com",
                collection_ids=["col-123"],
            )

            # Verify
            data = json.loads(content.decode("utf-8"))
            assert len(data["collections"]) == 1
            collection_service.repository.get_by_id.assert_called_once_with("col-123")

    async def test_export_includes_rules(
        self, collection_service, sample_collection, sample_rule
    ):
        """Test that export includes collection rules."""
        sample_rule.list_rule = "account_id = @account.id"
        collection_service.repository.list_all = AsyncMock(return_value=[sample_collection])

        with patch(
            "snackbase.infrastructure.persistence.repositories.collection_rule_repository.CollectionRuleRepository"
        ) as MockRuleRepo:
            mock_rule_repo = MagicMock()
            mock_rule_repo.get_by_collection_id = AsyncMock(return_value=sample_rule)
            MockRuleRepo.return_value = mock_rule_repo

            content, _ = await collection_service.export_collections(
                user_email="admin@example.com"
            )

            data = json.loads(content.decode("utf-8"))
            rules = data["collections"][0]["rules"]
            assert rules["list_rule"] == "account_id = @account.id"
            assert rules["list_fields"] == "*"


@pytest.mark.asyncio
class TestImportCollections:
    """Tests for import_collections method."""

    async def test_import_new_collection_with_migrations(
        self, collection_service, sample_collection
    ):
        """Test importing a new collection with migrations."""
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": "admin@example.com",
            "collections": [
                {
                    "name": "NewCollection",
                    "schema": [{"name": "title", "type": "text"}],
                    "rules": {"list_rule": "", "list_fields": "*"},
                }
            ],
        }

        # Mock repository - collection doesn't exist
        collection_service.repository.get_by_name = AsyncMock(return_value=None)

        # Mock create_collection
        with patch.object(
            collection_service, "create_collection", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = sample_collection

            result = await collection_service.import_collections(
                export_data=export_data,
                strategy="error",
                user_id="user-123",
            )

            assert result["success"] is True
            assert result["imported_count"] == 1
            assert result["skipped_count"] == 0
            assert result["failed_count"] == 0
            mock_create.assert_called_once()

    async def test_import_error_strategy_fails_on_existing(
        self, collection_service, sample_collection
    ):
        """Test that error strategy fails when collection exists."""
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": "admin@example.com",
            "collections": [
                {
                    "name": "TestCollection",
                    "schema": [{"name": "title", "type": "text"}],
                    "rules": {},
                }
            ],
        }

        # Mock repository - collection exists
        collection_service.repository.get_by_name = AsyncMock(return_value=sample_collection)

        result = await collection_service.import_collections(
            export_data=export_data,
            strategy="error",
            user_id="user-123",
        )

        assert result["success"] is False
        assert result["imported_count"] == 0
        assert result["failed_count"] == 1
        assert result["collections"][0]["status"] == "error"

    async def test_import_skip_strategy_skips_existing(
        self, collection_service, sample_collection
    ):
        """Test that skip strategy skips existing collections."""
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": "admin@example.com",
            "collections": [
                {
                    "name": "TestCollection",
                    "schema": [{"name": "title", "type": "text"}],
                    "rules": {},
                }
            ],
        }

        # Mock repository - collection exists
        collection_service.repository.get_by_name = AsyncMock(return_value=sample_collection)

        result = await collection_service.import_collections(
            export_data=export_data,
            strategy="skip",
            user_id="user-123",
        )

        assert result["success"] is True
        assert result["imported_count"] == 0
        assert result["skipped_count"] == 1
        assert result["collections"][0]["status"] == "skipped"

    async def test_import_update_strategy_updates_existing(
        self, collection_service, sample_collection
    ):
        """Test that update strategy updates existing collections."""
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": "admin@example.com",
            "collections": [
                {
                    "name": "TestCollection",
                    "schema": [
                        {"name": "title", "type": "text"},
                        {"name": "new_field", "type": "text"},
                    ],
                    "rules": {},
                }
            ],
        }

        # Mock repository - collection exists
        collection_service.repository.get_by_name = AsyncMock(return_value=sample_collection)

        # Mock update
        with patch.object(
            collection_service, "update_collection_schema", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = sample_collection

            result = await collection_service.import_collections(
                export_data=export_data,
                strategy="update",
                user_id="user-123",
            )

            assert result["success"] is True
            assert result["updated_count"] == 1
            mock_update.assert_called_once()

    async def test_import_invalid_version_fails(self, collection_service):
        """Test that invalid version raises error."""
        export_data = {
            "version": "2.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": "admin@example.com",
            "collections": [],
        }

        with pytest.raises(ValueError, match="Unsupported export version"):
            await collection_service.import_collections(
                export_data=export_data,
                strategy="error",
                user_id="user-123",
            )


class TestDependencySort:
    """Tests for _sort_collections_by_dependency method."""

    def test_sorts_by_reference_dependencies(self, collection_service):
        """Test that collections are sorted by reference dependencies."""
        collections = [
            {
                "name": "orders",
                "schema": [
                    {"name": "customer_id", "type": "reference", "collection": "customers"}
                ],
            },
            {"name": "customers", "schema": [{"name": "name", "type": "text"}]},
        ]

        sorted_collections = collection_service._sort_collections_by_dependency(collections)

        # Customers should come before orders
        names = [c["name"] for c in sorted_collections]
        assert names.index("customers") < names.index("orders")

    def test_handles_no_dependencies(self, collection_service):
        """Test sorting with no dependencies."""
        collections = [
            {"name": "a", "schema": [{"name": "x", "type": "text"}]},
            {"name": "b", "schema": [{"name": "y", "type": "text"}]},
        ]

        sorted_collections = collection_service._sort_collections_by_dependency(collections)

        assert len(sorted_collections) == 2

    def test_handles_circular_dependencies(self, collection_service):
        """Test that circular dependencies don't cause infinite loop."""
        collections = [
            {
                "name": "a",
                "schema": [{"name": "b_ref", "type": "reference", "collection": "b"}],
            },
            {
                "name": "b",
                "schema": [{"name": "a_ref", "type": "reference", "collection": "a"}],
            },
        ]

        # Should not hang
        sorted_collections = collection_service._sort_collections_by_dependency(collections)
        assert len(sorted_collections) == 2
