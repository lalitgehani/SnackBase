import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi import Request

from snackbase.infrastructure.api.routes.records_router import (
    create_record,
    list_records,
    get_record,
    update_record_full,
    update_record_partial,
    delete_record,
)
from snackbase.infrastructure.api.schemas import RecordValidationErrorDetail


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.user_id = "user-123"
    user.account_id = "acc-123"
    return user


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.query_params = {}
    return request


@pytest.fixture
def sample_schema():
    return [
        {"name": "title", "type": "text", "required": True},
        {"name": "count", "type": "number"},
        {"name": "is_active", "type": "boolean"},
        {"name": "ref_id", "type": "reference", "collection": "others"},
    ]


@pytest.fixture
def sample_collection(sample_schema):
    col = MagicMock()
    col.name = "posts"
    col.schema = json.dumps(sample_schema)
    return col


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.records_router.RecordValidator")
@pytest.mark.asyncio
async def test_create_record_success(
    mock_validator,
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    # Setup
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    mock_rec_repo.check_reference_exists = AsyncMock(return_value=True)
    
    # Mock insert result
    data = {"title": "New Post"}
    expected_record = {
        "id": "rec-new",
        "account_id": mock_user.account_id,
        "created_by": mock_user.user_id,
        "created_at": "2023-01-01",
        "updated_at": "2023-01-01",
        "updated_by": mock_user.user_id,
        "title": "New Post",
    }
    mock_rec_repo.insert_record = AsyncMock(return_value=expected_record)

    # Mock validator
    mock_validator.validate_and_apply_defaults.return_value = (data, [])

    # Act
    response = await create_record("posts", data, mock_user, mock_session)

    # Assert
    assert response.id == "rec-new"
    assert response.title == "New Post"
    
    mock_col_repo.get_by_name.assert_called_once_with("posts")
    mock_rec_repo.insert_record.assert_called_once()
    mock_session.commit.assert_called_once()


@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_create_record_collection_not_found(
    mock_col_repo_cls,
    mock_session,
    mock_user,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=None)

    response = await create_record("unknown", {}, mock_user, mock_session)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.records_router.RecordValidator")
@pytest.mark.asyncio
async def test_create_record_validation_error(
    mock_validator,
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    # Mock validation error
    error = RecordValidationErrorDetail(field="title", message="Required", code="missing")
    # Return tuple (processed_data, errors)
    mock_validator.validate_and_apply_defaults.return_value = ({}, [error])

    response = await create_record("posts", {}, mock_user, mock_session)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = json.loads(response.body.decode())
    assert body["error"] == "Validation error"
    assert body["details"][0]["field"] == "title"


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_list_records_success(
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    mock_request,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    records = [
        {
            "id": "1", 
            "title": "A", 
            "created_at": "2023",
            "account_id": "acc-1", 
            "created_by": "user-1", 
            "updated_at": "2023", 
            "updated_by": "user-1"
        },
        {
            "id": "2", 
            "title": "B", 
            "created_at": "2023",
            "account_id": "acc-1", 
            "created_by": "user-1", 
            "updated_at": "2023", 
            "updated_by": "user-1"
        },
    ]
    mock_rec_repo.find_all = AsyncMock(return_value=(records, 2))

    response = await list_records(
        "posts", mock_request, mock_user, skip=0, limit=10, sort="-created_at", fields=None, session=mock_session
    )

    assert response.total == 2
    assert len(response.items) == 2
    assert response.items[0].title == "A"


@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_list_records_collection_not_found(
    mock_col_repo_cls,
    mock_session,
    mock_user,
    mock_request,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=None)

    response = await list_records("unknown", mock_request, mock_user, session=mock_session)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_get_record_success(
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    record = {
        "id": "rec-1", 
        "title": "My Post", 
        "created_at": "2023",
        "account_id": "acc-1", 
        "created_by": "user-1", 
        "updated_at": "2023", 
        "updated_by": "user-1"
    }
    mock_rec_repo.get_by_id = AsyncMock(return_value=record)

    response = await get_record("posts", "rec-1", mock_user, mock_session)

    assert response.id == "rec-1"
    assert response.title == "My Post"


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_get_record_not_found(
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    mock_rec_repo.get_by_id = AsyncMock(return_value=None)

    response = await get_record("posts", "rec-missing", mock_user, mock_session)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@patch("snackbase.infrastructure.api.routes.records_router.RecordValidator")
@pytest.mark.asyncio
async def test_update_record_success(
    mock_validator,
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    updated_record = {
        "id": "rec-1",
        "title": "Updated",
        "created_at": "2023",
        "updated_at": "2023-new",
        "account_id": "acc-1",
        "created_by": "user-1",
        "updated_by": "user-1"
    }
    mock_rec_repo.update_record = AsyncMock(return_value=updated_record)

    mock_validator.validate_and_apply_defaults.return_value = ({"title": "Updated"}, [])

    response = await update_record_partial("posts", "rec-1", {"title": "Updated"}, mock_user, mock_session)

    assert response.title == "Updated"
    mock_rec_repo.update_record.assert_called_once()
    mock_session.commit.assert_called_once()


@patch("snackbase.infrastructure.api.routes.records_router.RecordRepository")
@patch("snackbase.infrastructure.api.routes.records_router.CollectionRepository")
@pytest.mark.asyncio
async def test_delete_record_success(
    mock_col_repo_cls,
    mock_rec_repo_cls,
    mock_session,
    mock_user,
    sample_collection,
):
    mock_col_repo = mock_col_repo_cls.return_value
    mock_col_repo.get_by_name = AsyncMock(return_value=sample_collection)

    mock_rec_repo = mock_rec_repo_cls.return_value
    mock_rec_repo.delete_record = AsyncMock(return_value=True)

    response = await delete_record("posts", "rec-1", mock_user, mock_session)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_rec_repo.delete_record.assert_called_once()
    mock_session.commit.assert_called_once()
