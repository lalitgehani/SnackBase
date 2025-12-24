"""Unit tests for CollectionRepository."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories.collection_repository import (
    CollectionRepository,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session):
    """Create a CollectionRepository instance with a mock session."""
    return CollectionRepository(mock_session)


@pytest.mark.asyncio
async def test_create_collection(repository, mock_session):
    """Test creating a new collection."""
    collection = CollectionModel(
        id="test-id",
        name="test_collection",
        schema='[{"name": "field1", "type": "text"}]',
    )

    result = await repository.create(collection)

    mock_session.add.assert_called_once_with(collection)
    mock_session.flush.assert_called_once()
    assert result == collection


@pytest.mark.asyncio
async def test_get_by_name(repository, mock_session):
    """Test getting a collection by name."""
    collection_name = "test_collection"
    expected_collection = CollectionModel(
        id="test-id",
        name=collection_name,
        schema='[{"name": "field1", "type": "text"}]',
    )
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_collection
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_name(collection_name)

    mock_session.execute.assert_called_once()
    assert result == expected_collection


@pytest.mark.asyncio
async def test_get_by_name_not_found(repository, mock_session):
    """Test getting a non-existent collection by name."""
    collection_name = "non_existent"
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_name(collection_name)

    mock_session.execute.assert_called_once()
    assert result is None


@pytest.mark.asyncio
async def test_name_exists_true(repository, mock_session):
    """Test checking if a name exists (true case)."""
    collection_name = "existing_collection"
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "some-id"
    mock_session.execute.return_value = mock_result

    result = await repository.name_exists(collection_name)

    mock_session.execute.assert_called_once()
    assert result is True


@pytest.mark.asyncio
async def test_name_exists_false(repository, mock_session):
    """Test checking if a name exists (false case)."""
    collection_name = "new_collection"
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.name_exists(collection_name)

    mock_session.execute.assert_called_once()
    assert result is False


@pytest.mark.asyncio
async def test_get_by_id(repository, mock_session):
    """Test getting a collection by ID."""
    collection_id = "test-id"
    expected_collection = CollectionModel(
        id=collection_id,
        name="test_collection",
        schema='[{"name": "field1", "type": "text"}]',
    )
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_collection
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(collection_id)

    mock_session.execute.assert_called_once()
    assert result == expected_collection
