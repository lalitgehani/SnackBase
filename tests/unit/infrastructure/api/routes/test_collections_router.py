"""Unit tests for CollectionsRouter."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import JSONResponse

from snackbase.domain.services import CollectionValidationError
from snackbase.infrastructure.api.routes.collections_router import create_collection
from snackbase.infrastructure.api.schemas import CreateCollectionRequest, FieldDefinition
from snackbase.infrastructure.persistence.models import CollectionModel


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    # Mock session.bind to return a mock engine
    mock_engine = MagicMock()
    session.bind = mock_engine
    return session


@pytest.fixture
def mock_user():
    """Create a mock superadmin user."""
    user = MagicMock()
    user.user_id = "user-123"
    return user


@pytest.fixture
def valid_request():
    """Create a valid collection creation request."""
    return CreateCollectionRequest(
        name="TestCollection",
        fields=[
            FieldDefinition(name="title", type="text", required=True),
            FieldDefinition(name="count", type="number", default=0),
        ],
    )


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionService")
@pytest.mark.asyncio
async def test_create_collection_success(
    mock_service_cls,
    mock_session,
    mock_user,
    valid_request,
):
    """Test successful collection creation."""
    # Setup mocks
    mock_service = mock_service_cls.return_value
    
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema='[{"name": "title", "type": "text", "required": true}, {"name": "count", "type": "number", "default": 0}]',
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_service.create_collection = AsyncMock(return_value=collection)
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)

    # Verify
    mock_service.create_collection.assert_called_once()
    assert response.name == "TestCollection"
    assert response.id == "col-123"


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionService")
@pytest.mark.asyncio
async def test_create_collection_validation_error(
    mock_service_cls,
    mock_session,
    mock_user,
    valid_request,
):
    """Test collection creation with validation errors."""
    # Setup mock to return errors
    mock_service = mock_service_cls.return_value
    mock_service.create_collection = AsyncMock(side_effect=ValueError("Validation failed: name: Invalid name"))
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)
    
    # Verify
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.body.decode()
    assert "Validation error" in body
    assert "Validation failed" in body


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionService")
@pytest.mark.asyncio
async def test_create_collection_name_conflict(
    mock_service_cls,
    mock_session,
    mock_user,
    valid_request,
):
    """Test collection creation when name already exists."""
    # Setup
    mock_service = mock_service_cls.return_value
    mock_service.create_collection = AsyncMock(side_effect=ValueError("Collection 'TestCollection' already exists"))
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)
    
    # Verify
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.body.decode()


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionService")
@pytest.mark.asyncio
async def test_create_collection_table_creation_error(
    mock_service_cls,
    mock_session,
    mock_user,
    valid_request,
):
    """Test handling of table creation errors."""
    # Setup
    mock_service = mock_service_cls.return_value
    mock_service.create_collection = AsyncMock(side_effect=Exception("DB error"))
    
    # Execute
    with pytest.raises(Exception, match="DB error"):
        await create_collection(valid_request, mock_user, mock_session)


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionService")
@pytest.mark.asyncio
async def test_create_collection_with_pii_fields(
    mock_service_cls,
    mock_session,
    mock_user,
):
    """Test collection creation with PII fields preserves metadata."""
    # Create request with PII fields
    request = CreateCollectionRequest(
        name="Customers",
        fields=[
            FieldDefinition(name="email", type="email", pii=True, mask_type="email"),
            FieldDefinition(name="ssn", type="text", pii=True, mask_type="ssn"),
            FieldDefinition(name="name", type="text", required=True),
        ],
    )
    
    # Setup mocks
    mock_service = mock_service_cls.return_value
    
    collection = CollectionModel(
        id="col-456",
        name="Customers",
        schema='[{"name": "email", "type": "email", "pii": true, "mask_type": "email"}, {"name": "ssn", "type": "text", "pii": true, "mask_type": "ssn"}, {"name": "name", "type": "text", "required": true, "pii": false, "mask_type": null}]',
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_service.create_collection = AsyncMock(return_value=collection)
    
    # Execute
    response = await create_collection(request, mock_user, mock_session)

    # Verify
    assert response.name == "Customers"
    assert len(response.fields) == 3
    
    # Check PII metadata is preserved
    email_field = next(f for f in response.fields if f.name == "email")
    assert email_field.pii is True
    assert email_field.mask_type == "email"
    
    ssn_field = next(f for f in response.fields if f.name == "ssn")
    assert ssn_field.pii is True
    assert ssn_field.mask_type == "ssn"
    
    name_field = next(f for f in response.fields if f.name == "name")
    assert name_field.pii is False
    assert name_field.mask_type is None
