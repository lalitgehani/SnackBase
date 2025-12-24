"""Unit tests for TableBuilder."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.domain.services.collection_validator import FieldType, OnDeleteAction
from snackbase.infrastructure.persistence.table_builder import SYSTEM_COLUMNS

def test_generate_table_name():
    """Test generating a table name from a collection name."""
    assert TableBuilder.generate_table_name("MyCollection") == "col_mycollection"
    assert TableBuilder.generate_table_name("users") == "col_users"
    assert TableBuilder.generate_table_name("TEST") == "col_test"

def test_build_column_def_text():
    """Test building a text column definition."""
    field = {
        "name": "title",
        "type": FieldType.TEXT.value,
        "required": True,
        "default": "Untitled"
    }
    col_def, fk = TableBuilder.build_column_def(field, "col_posts")
    assert col_def == '"title" TEXT NOT NULL DEFAULT \'Untitled\''
    assert fk is None

def test_build_column_def_number():
    """Test building a number column definition."""
    field = {
        "name": "price",
        "type": FieldType.NUMBER.value,
        "default": 0.0
    }
    col_def, fk = TableBuilder.build_column_def(field, "col_products")
    assert col_def == '"price" REAL DEFAULT 0.0'
    assert fk is None

def test_build_column_def_boolean():
    """Test building a boolean column definition."""
    field = {
        "name": "is_active",
        "type": FieldType.BOOLEAN.value,
        "default": True
    }
    col_def, fk = TableBuilder.build_column_def(field, "col_users")
    assert col_def == '"is_active" INTEGER DEFAULT 1'
    assert fk is None

def test_build_column_def_unique():
    """Test building a unique column definition."""
    field = {
        "name": "slug",
        "type": FieldType.TEXT.value,
        "unique": True
    }
    col_def, fk = TableBuilder.build_column_def(field, "col_posts")
    assert col_def == '"slug" TEXT UNIQUE'
    assert fk is None

def test_build_column_def_reference():
    """Test building a reference column definition."""
    field = {
        "name": "author_id",
        "type": FieldType.REFERENCE.value,
        "collection": "authors",
        "on_delete": OnDeleteAction.CASCADE.value
    }
    col_def, fk = TableBuilder.build_column_def(field, "col_posts")
    assert col_def == '"author_id" TEXT'
    assert fk == 'FOREIGN KEY ("author_id") REFERENCES "col_authors"("id") ON DELETE CASCADE'

def test_build_create_table_ddl():
    """Test building the full CREATE TABLE DDL."""
    collection_name = "posts"
    schema = [
        {"name": "title", "type": FieldType.TEXT.value, "required": True},
        {"name": "views", "type": FieldType.NUMBER.value, "default": 0}
    ]
    
    ddl = TableBuilder.build_create_table_ddl(collection_name, schema)
    
    assert 'CREATE TABLE "col_posts"' in ddl
    
    # Check system columns
    for col, col_type in SYSTEM_COLUMNS:
        assert f'"{col}" {col_type}' in ddl
        
    # Check user columns
    assert '"title" TEXT NOT NULL' in ddl
    assert '"views" REAL DEFAULT 0' in ddl

def test_build_index_ddl():
    """Test building index DDL statements."""
    collection_name = "posts"
    schema = [
        {"name": "slug", "type": FieldType.TEXT.value, "unique": True},
        {"name": "author_id", "type": FieldType.REFERENCE.value, "collection": "authors"}
    ]
    
    indexes = TableBuilder.build_index_ddl(collection_name, schema)
    
    # Needs to cover account_id, unique fields, and reference fields
    # But wait, unique fields might NOT get explicit indexes if UNIQUE constraint is enough for SQLite?
    # Let's check the code: TableBuilder actually DOES create explicit indexes for reference fields AND account_id
    # And it loops through schema to index reference fields.
    
    assert len(indexes) == 2 # 1 for account_id + 1 for reference field author_id. Unique slug usually handled by constraint but check code.
    
    # Let's re-read TableBuilder.build_index_ddl from the previous turn...
    # It does: indexes.append(account_id)
    # Then loops schema: if field_type == REFERENCE => indexes.append(name)
    # It does NOT add index for unique fields explicitly in the loop shown in previous turn unless I misread.
    # Re-reading step 26: 
    # line 177: if field_type == FieldType.REFERENCE.value:
    # So it only explicitly indexes references in that loop.
    
    assert any('ON "col_posts"("account_id")' in idx for idx in indexes)
    assert any('ON "col_posts"("author_id")' in idx for idx in indexes)

@pytest.mark.asyncio
async def test_table_exists_true():
    """Test checking if table exists (true case)."""
    engine = AsyncMock(spec=AsyncEngine)
    mock_conn = AsyncMock()
    engine.connect.return_value.__aenter__.return_value = mock_conn
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "col_posts"
    mock_conn.execute.return_value = mock_result
    
    exists = await TableBuilder.table_exists(engine, "posts")
    
    assert exists is True
    engine.connect.assert_called_once()
    mock_conn.execute.assert_called_once()

@pytest.mark.asyncio
async def test_table_exists_false():
    """Test checking if table exists (false case)."""
    engine = AsyncMock(spec=AsyncEngine)
    mock_conn = AsyncMock()
    engine.connect.return_value.__aenter__.return_value = mock_conn
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_conn.execute.return_value = mock_result
    
    exists = await TableBuilder.table_exists(engine, "new_table")
    
    assert exists is False
