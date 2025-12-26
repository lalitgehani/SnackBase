"""Unit tests for CollectionsRouter."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import JSONResponse

from snackbase.domain.services import CollectionValidator, CollectionValidationError
from snackbase.infrastructure.api.routes.collections_router import create_collection
from snackbase.infrastructure.api.schemas import CreateCollectionRequest, FieldDefinition


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
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


@patch("snackbase.infrastructure.api.routes.collections_router.TableBuilder")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionValidator")
@pytest.mark.asyncio
async def test_create_collection_success(
    mock_validator,
    mock_repo_cls,
    mock_table_builder,
    mock_session,
    mock_user,
    valid_request,
):
    """Test successful collection creation."""
    # Setup mocks
    mock_validator.validate.return_value = []  # No errors
    
    mock_repo = mock_repo_cls.return_value
    mock_repo.name_exists = AsyncMock(return_value=False)
    mock_repo.create = AsyncMock()
    
    mock_table_builder.create_table = AsyncMock()
    mock_table_builder.generate_table_name.return_value = "col_testcollection"
    
    # Mock session.bind to return a mock engine
    mock_engine = MagicMock()
    mock_session.bind = mock_engine
    
    # Mock session.refresh to populate timestamps
    async def mock_refresh(instance):
        instance.created_at = datetime.now()
        instance.updated_at = datetime.now()

    mock_session.refresh.side_effect = mock_refresh
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)

    # Verify
    mock_validator.validate.assert_called_once()
    mock_repo.name_exists.assert_called_once_with("TestCollection")
    mock_table_builder.create_table.assert_called_once()
    mock_repo.create.assert_called_once()
    mock_session.commit.assert_called_once()
    
    assert response.name == "TestCollection"
    assert response.table_name == "col_testcollection"
    assert len(response.fields) == 2


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionValidator")
@pytest.mark.asyncio
async def test_create_collection_validation_error(
    mock_validator,
    mock_session,
    mock_user,
    valid_request,
):
    """Test collection creation with validation errors."""
    # Setup mock to return errors
    error = CollectionValidationError(field="name", message="Invalid name", code="invalid")
    mock_validator.validate.return_value = [error]
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)
    
    # Verify
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.body.decode()
    assert "Validation error" in body
    assert "Invalid name" in body


@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionValidator")
@pytest.mark.asyncio
async def test_create_collection_name_conflict(
    mock_validator,
    mock_repo_cls,
    mock_session,
    mock_user,
    valid_request,
):
    """Test collection creation when name already exists."""
    # Setup
    mock_validator.validate.return_value = []
    mock_repo = mock_repo_cls.return_value
    mock_repo.name_exists = AsyncMock(return_value=True)
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)
    
    # Verify
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.body.decode()


@patch("snackbase.infrastructure.api.routes.collections_router.TableBuilder")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionValidator")
@pytest.mark.asyncio
async def test_create_collection_table_creation_error(
    mock_validator,
    mock_repo_cls,
    mock_table_builder,
    mock_session,
    mock_user,
    valid_request,
):
    """Test handling of table creation errors."""
    # Setup
    mock_validator.validate.return_value = []
    mock_repo = mock_repo_cls.return_value
    mock_repo.name_exists = AsyncMock(return_value=False)
    
    # Make table creation fail
    mock_table_builder.create_table = AsyncMock(side_effect=Exception("DB error"))
    mock_table_builder.generate_table_name.return_value = "col_testcollection"
    
    # Mock session.bind to return a mock engine
    mock_engine = MagicMock()
    mock_session.bind = mock_engine
    
    # Execute
    response = await create_collection(valid_request, mock_user, mock_session)
    
    # Verify
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to create collection table" in response.body.decode()


@patch("snackbase.infrastructure.api.routes.collections_router.TableBuilder")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.collections_router.CollectionValidator")
@pytest.mark.asyncio
async def test_create_collection_with_pii_fields(
    mock_validator,
    mock_repo_cls,
    mock_table_builder,
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
    mock_validator.validate.return_value = []
    
    mock_repo = mock_repo_cls.return_value
    mock_repo.name_exists = AsyncMock(return_value=False)
    mock_repo.create = AsyncMock()
    
    mock_table_builder.create_table = AsyncMock()
    mock_table_builder.generate_table_name.return_value = "col_customers"
    
    # Mock session.bind to return a mock engine
    mock_engine = MagicMock()
    mock_session.bind = mock_engine
    
    # Mock session.refresh to populate timestamps
    async def mock_refresh(instance):
        instance.created_at = datetime.now()
        instance.updated_at = datetime.now()

    mock_session.refresh.side_effect = mock_refresh
    
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
