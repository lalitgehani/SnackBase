import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from snackbase.infrastructure.persistence.repositories.record_repository import RecordRepository


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def repository(mock_session):
    return RecordRepository(mock_session)


@pytest.fixture
def sample_schema():
    return [
        {"name": "title", "type": "text", "required": True},
        {"name": "count", "type": "number"},
        {"name": "is_active", "type": "boolean"},
        {"name": "metadata", "type": "json"},
    ]


@pytest.mark.asyncio
async def test_insert_record(repository, mock_session, sample_schema):
    # Arrange
    collection_name = "posts"
    record_id = "rec_123"
    account_id = "acc_123"
    created_by = "usr_123"
    data = {
        "title": "Test Post",
        "count": 10,
        "is_active": True,
        "metadata": {"tags": ["a", "b"]},
    }
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        result = await repository.insert_record(
            collection_name, record_id, account_id, created_by, data, sample_schema
        )

    # Assert
    assert result["id"] == record_id
    assert result["account_id"] == account_id
    assert result["title"] == "Test Post"
    assert result["metadata"] == {"tags": ["a", "b"]}
    
    # Verify SQL execution
    mock_session.execute.assert_called_once()
    args = mock_session.execute.call_args[0]
    assert "INSERT INTO" in str(args[0])
    assert '"sb_posts"' in str(args[0])
    
    # Verify params
    params = args[1]
    assert params["title"] == "Test Post"
    assert params["is_active"] == 1  # Boolean converted to int
    assert params["metadata"] == '{"tags": ["a", "b"]}'  # JSON dumped
    assert isinstance(params["created_at"], datetime)
    assert isinstance(params["updated_at"], datetime)


@pytest.mark.asyncio
async def test_get_by_id(repository, mock_session, sample_schema):
    # Arrange
    collection_name = "posts"
    record_id = "rec_123"
    account_id = "acc_123"
    
    # Mock result row
    row = MagicMock()
    row._mapping = {
        "id": record_id,
        "account_id": account_id,
        "title": "Test Post",
        "count": 10,
        "is_active": 1,
        "metadata": '{"tags": ["a", "b"]}',
        "created_at": "2023-01-01T00:00:00",
    }
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row
    mock_session.execute.return_value = mock_result
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        result = await repository.get_by_id(collection_name, record_id, account_id, sample_schema)
        
    # Assert
    assert result is not None
    assert result["id"] == record_id
    assert result["is_active"] is True  # Converted back to bool
    assert result["metadata"] == {"tags": ["a", "b"]}  # Converted back to dict
    assert result["title"] == "Test Post"


@pytest.mark.asyncio
async def test_get_by_id_not_found(repository, mock_session, sample_schema):
    # Arrange
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        result = await repository.get_by_id("posts", "rec_not_found", "acc_123", sample_schema)
        
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_update_record(repository, mock_session, sample_schema):
    # Arrange
    collection_name = "posts"
    record_id = "rec_123"
    account_id = "acc_123"
    updated_by = "usr_123"
    data = {
        "title": "Updated Title",
        "is_active": False,
    }
    
    # Mock result row (returning *)
    row = MagicMock()
    row._mapping = {
        "id": record_id,
        "account_id": account_id,
        "title": "Updated Title",
        "is_active": 0,
        "metadata": '{"tags": ["a"]}', # Unchanged field
        "updated_by": updated_by,
    }
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row
    mock_session.execute.return_value = mock_result
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        result = await repository.update_record(
            collection_name, record_id, account_id, updated_by, data, sample_schema
        )
        
    # Assert
    assert result is not None
    assert result["title"] == "Updated Title"
    assert result["is_active"] is False
    
    # Verify SQL
    args = mock_session.execute.call_args[0]
    assert "UPDATE" in str(args[0])
    params = args[1]
    assert params["title"] == "Updated Title"
    assert params["is_active"] == 0
    assert params["updated_by"] == updated_by
    assert isinstance(params["updated_at"], datetime)


@pytest.mark.asyncio
async def test_delete_record(repository, mock_session):
    # Arrange
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute.return_value = mock_result
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        result = await repository.delete_record("posts", "rec_123", "acc_123")
        
    # Assert
    assert result is True
    
    # Verify SQL
    args = mock_session.execute.call_args[0]
    assert "DELETE FROM" in str(args[0])


@pytest.mark.asyncio
async def test_find_all(repository, mock_session, sample_schema):
    # Arrange
    collection_name = "posts"
    account_id = "acc_123"
    
    # Mock count result
    count_result = MagicMock()
    count_result.scalar_one.return_value = 2
    
    # Mock rows result
    row1 = MagicMock()
    row1._mapping = {"id": "1", "title": "A", "count": 1, "is_active": 1}
    row2 = MagicMock()
    row2._mapping = {"id": "2", "title": "B", "count": 2, "is_active": 0}
    
    rows_result = MagicMock()
    rows_result.fetchall.return_value = [row1, row2]
    
    # Use side_effect to return different results for consecutive calls
    mock_session.execute.side_effect = [count_result, rows_result]
    
    # Act
    with patch("snackbase.infrastructure.persistence.repositories.record_repository.TableBuilder.generate_table_name") as mock_table_name:
        mock_table_name.return_value = "sb_posts"
        records, total = await repository.find_all(
            collection_name, account_id, sample_schema, sort_by="count", descending=False
        )
        
    # Assert
    assert total == 2
    assert len(records) == 2
    assert records[0]["title"] == "A"
    assert records[0]["is_active"] is True
    assert records[1]["title"] == "B"
    assert records[1]["is_active"] is False
    
    # Verify SQL
    assert mock_session.execute.call_count == 2
    
    # Check find logic
    select_call = mock_session.execute.call_args_list[1]
    assert "ORDER BY" in str(select_call[0][0])
    assert '"count" ASC' in str(select_call[0][0])
