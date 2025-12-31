"""Unit tests for CollectionService."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from snackbase.domain.services import CollectionService, CollectionValidationError
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
    )
    return collection


class TestValidateSchemaUpdate:
    """Tests for validate_schema_update method."""

    def test_no_changes_valid(self, collection_service, sample_schema):
        """Test that identical schemas are valid."""
        errors = collection_service.validate_schema_update(sample_schema, sample_schema)
        assert len(errors) == 0

    def test_add_new_field_valid(self, collection_service, sample_schema):
        """Test that adding new fields is valid."""
        new_schema = sample_schema + [{"name": "description", "type": "text"}]
        errors = collection_service.validate_schema_update(sample_schema, new_schema)
        assert len(errors) == 0

    def test_field_deletion_invalid(self, collection_service, sample_schema):
        """Test that deleting fields is not allowed."""
        new_schema = [sample_schema[0]]  # Remove second field
        errors = collection_service.validate_schema_update(sample_schema, new_schema)
        
        assert len(errors) == 1
        assert errors[0].field == "count"
        assert "deletion" in errors[0].message.lower()
        assert errors[0].code == "field_deletion_not_allowed"

    def test_type_change_invalid(self, collection_service, sample_schema):
        """Test that changing field types is not allowed."""
        new_schema = [
            {"name": "title", "type": "number"},  # Changed from text to number
            sample_schema[1],
        ]
        errors = collection_service.validate_schema_update(sample_schema, new_schema)
        
        assert len(errors) == 1
        assert errors[0].field == "title"
        assert "type change" in errors[0].message.lower()
        assert errors[0].code == "type_change_not_allowed"

    def test_multiple_violations(self, collection_service, sample_schema):
        """Test multiple validation errors."""
        new_schema = [
            {"name": "title", "type": "number"},  # Type change
            # count field deleted
        ]
        errors = collection_service.validate_schema_update(sample_schema, new_schema)
        
        assert len(errors) == 2


@pytest.mark.asyncio
class TestUpdateCollectionSchema:
    """Tests for update_collection_schema method."""

    async def test_update_success_no_new_fields(
        self, collection_service, sample_collection, sample_schema
    ):
        """Test successful update with no new fields."""
        # Mock repository
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)
        collection_service.repository.update = AsyncMock(return_value=sample_collection)
        
        # Update with same schema
        result = await collection_service.update_collection_schema("col-123", sample_schema)
        
        assert result == sample_collection
        collection_service.repository.get_by_id.assert_called_once_with("col-123")
        collection_service.repository.update.assert_called_once()

    async def test_update_success_with_new_fields(
        self, collection_service, sample_collection, sample_schema, mock_engine
    ):
        """Test successful update with new fields."""
        from unittest.mock import patch
        
        # Mock repository
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)
        collection_service.repository.update = AsyncMock(return_value=sample_collection)
        
        # New schema with additional field
        new_schema = sample_schema + [{"name": "description", "type": "text"}]
        
        # Mock TableBuilder
        with patch("snackbase.domain.services.collection_service.TableBuilder") as mock_tb:
            mock_tb.add_columns = AsyncMock()
            
            result = await collection_service.update_collection_schema("col-123", new_schema)
            
            # Verify MigrationService was called
            collection_service.migration_service.generate_update_collection_migration.assert_called_once()
            collection_service.migration_service.apply_migrations.assert_called_once()

    async def test_update_collection_not_found(self, collection_service, sample_schema):
        """Test update when collection doesn't exist."""
        collection_service.repository.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="not found"):
            await collection_service.update_collection_schema("col-999", sample_schema)

    async def test_update_validation_error(
        self, collection_service, sample_collection, sample_schema
    ):
        """Test update with validation errors."""
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)
        
        # Try to change field type
        invalid_schema = [{"name": "title", "type": "number"}]
        
        with pytest.raises(ValueError, match="validation failed"):
            await collection_service.update_collection_schema("col-123", invalid_schema)


@pytest.mark.asyncio
class TestDeleteCollection:
    """Tests for delete_collection method."""

    async def test_delete_success(self, collection_service, sample_collection):
        """Test successful collection deletion."""
        from unittest.mock import patch
        
        # Mock repository
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)
        collection_service.repository.get_record_count = AsyncMock(return_value=42)
        collection_service.repository.delete = AsyncMock()
        
        # Mock TableBuilder
        with patch("snackbase.domain.services.collection_service.TableBuilder") as mock_tb:
            mock_tb.generate_table_name.return_value = "col_testcollection"
            mock_tb.drop_table = AsyncMock()
            
            result = await collection_service.delete_collection("col-123")
            
            # Verify result
            assert result["collection_id"] == "col-123"
            assert result["collection_name"] == "TestCollection"
            assert result["records_deleted"] == 42
            
            # Verify calls
            collection_service.migration_service.generate_delete_collection_migration.assert_called_once()
            collection_service.migration_service.apply_migrations.assert_called_once()
            collection_service.repository.delete.assert_called_once()

    async def test_delete_collection_not_found(self, collection_service):
        """Test delete when collection doesn't exist."""
        collection_service.repository.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="not found"):
            await collection_service.delete_collection("col-999")


@pytest.mark.asyncio
class TestGetRecordCount:
    """Tests for get_record_count method."""

    async def test_get_record_count_success(self, collection_service, sample_collection):
        """Test successful record count retrieval."""
        from unittest.mock import patch
        
        collection_service.repository.get_by_id = AsyncMock(return_value=sample_collection)
        collection_service.repository.get_record_count = AsyncMock(return_value=100)
        
        with patch("snackbase.domain.services.collection_service.TableBuilder") as mock_tb:
            mock_tb.generate_table_name.return_value = "col_testcollection"
            
            count = await collection_service.get_record_count("col-123")
            
            assert count == 100
            collection_service.repository.get_record_count.assert_called_once_with(
                "col_testcollection"
            )

    async def test_get_record_count_not_found(self, collection_service):
        """Test record count when collection doesn't exist."""
        collection_service.repository.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="not found"):
            await collection_service.get_record_count("col-999")
