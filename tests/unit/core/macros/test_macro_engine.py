"""Unit tests for Macro Execution Engine."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.expression import TextClause

from snackbase.core.macros.engine import MacroExecutionEngine
from snackbase.infrastructure.persistence.models.macro import MacroModel


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = AsyncMock()
    return session


@pytest.fixture
def macro_engine(mock_session):
    """Create a MacroExecutionEngine with mocked dependencies."""
    engine = MacroExecutionEngine(mock_session)
    # Mock the internal repository directly to avoid DB calls
    engine.macro_repo = AsyncMock()
    return engine


@pytest.mark.asyncio
async def test_builtin_has_group(macro_engine):
    """Test @has_group built-in macro."""
    # Dict user
    context = {"user": {"groups": ["admin", "editor"]}}
    assert await macro_engine.execute_macro("@has_group", ["admin"], context) is True
    assert await macro_engine.execute_macro("@has_group", ["guest"], context) is False
    
    # Object user
    class User:
        groups = ["admin"]
    context_obj = {"user": User()}
    assert await macro_engine.execute_macro("@has_group", ["admin"], context_obj) is True
    
    # Missing user
    assert await macro_engine.execute_macro("@has_group", ["admin"], {}) is False


@pytest.mark.asyncio
async def test_builtin_has_role(macro_engine):
    """Test @has_role built-in macro."""
    context = {"user": {"role": "admin"}}
    assert await macro_engine.execute_macro("@has_role", ["admin"], context) is True
    assert await macro_engine.execute_macro("@has_role", ["user"], context) is False


@pytest.mark.asyncio
async def test_builtin_owns_record(macro_engine):
    """Test @owns_record built-in macro."""
    context = {"user": {"id": 1}, "record": {"owner_id": 1}}
    assert await macro_engine.execute_macro("@owns_record", [], context) is True
    
    context_diff = {"user": {"id": 1}, "record": {"owner_id": 2}}
    assert await macro_engine.execute_macro("@owns_record", [], context_diff) is False


@pytest.mark.asyncio
async def test_builtin_in_time_range(macro_engine):
    """Test @in_time_range built-in macro."""
    from datetime import datetime
    current = datetime.now().hour
    
    # Range covering current hour
    start = current - 1
    end = current + 2
    assert await macro_engine.execute_macro("@in_time_range", [start, end], {}) is True
    
    # Range outside
    assert await macro_engine.execute_macro("@in_time_range", [current + 1, current + 2], {}) is False


@pytest.mark.asyncio
async def test_builtin_has_permission(macro_engine):
    """Test @has_permission built-in macro."""
    context = {
        "permissions": {
            "posts": ["create", "read"]
        }
    }
    assert await macro_engine.execute_macro("@has_permission", ["create", "posts"], context) is True
    assert await macro_engine.execute_macro("@has_permission", ["delete", "posts"], context) is False
    assert await macro_engine.execute_macro("@has_permission", ["create", "comments"], context) is False


@pytest.mark.asyncio
async def test_sql_macro_execution(macro_engine, mock_session):
    """Test execution of stored SQL macro."""
    # Setup mock macro
    macro_name = "check_status"
    macro_sql = "SELECT 1 FROM records WHERE status = :status"
    parameters = ["status"]
    
    macro = MacroModel(
        name=macro_name,
        sql_query=macro_sql,
        parameters=json.dumps(parameters)
    )
    
    # Configure repo to return macro
    macro_engine.macro_repo.get_by_name.return_value = macro
    
    # Configure session execution
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    macro_engine.session.execute.return_value = mock_result
    
    # Execute
    result = await macro_engine.execute_macro("@check_status", ["active"], {})
    
    assert result is True
    
    # Verify DB interaction
    macro_engine.macro_repo.get_by_name.assert_called_with("check_status")
    
    # Verify execute called
    # We can check arguments somewhat loosely
    assert macro_engine.session.execute.called
    call_args = macro_engine.session.execute.call_args
    # The first arg should be the TextClause
    # We can't easily inspect the bound params in the TextClause object from here without deeper introspection
    # But ensuring it was called is a good start.


@pytest.mark.asyncio
async def test_sql_macro_not_found(macro_engine):
    """Test executing non-existent macro."""
    macro_engine.macro_repo.get_by_name.return_value = None
    
    result = await macro_engine.execute_macro("@unknown", [], {})
    assert result is False
