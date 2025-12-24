"""Unit tests for Macro Execution Caching and Timeout."""

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
    engine.macro_repo = AsyncMock()
    return engine

@pytest.mark.asyncio
async def test_macro_caching(macro_engine):
    """Test that macro results are cached."""
    # Setup
    macro_name = "cached_macro"
    macro = MacroModel(
        name=macro_name,
        sql_query="SELECT :p1",
        parameters='["p1"]'
    )
    macro_engine.macro_repo.get_by_name.return_value = macro
    
    # Configure session execution
    mock_result = MagicMock()
    mock_result.scalar.return_value = 100
    macro_engine.session.execute.return_value = mock_result
    
    # First call
    result1 = await macro_engine.execute_macro("@cached_macro", [1], {})
    assert result1 == 100
    assert macro_engine.session.execute.call_count == 1
    
    # Second call (should hit cache)
    result2 = await macro_engine.execute_macro("@cached_macro", [1], {})
    assert result2 == 100
    assert macro_engine.session.execute.call_count == 1  # Call count remains 1
    
    # Different args (should not hit cache)
    result3 = await macro_engine.execute_macro("@cached_macro", [2], {})
    assert result3 == 100
    assert macro_engine.session.execute.call_count == 2  # Call count increases

@pytest.mark.asyncio
async def test_macro_timeout(macro_engine):
    """Test that timeout option is applied."""
    macro = MacroModel(
        name="timeout_macro",
        sql_query="SELECT SLEEP(10)",
        parameters='[]'
    )
    macro_engine.macro_repo.get_by_name.return_value = macro
    
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    macro_engine.session.execute.return_value = mock_result
    
    await macro_engine.execute_macro("@timeout_macro", [], {})
    
    # Verify execution_options called on the statement text object
    # This is tricky because text() creates a TextClause which we call .bindparams() then .execution_options() on.
    # The session.execute receives the FINAL object.
    
    args, _ = macro_engine.session.execute.call_args
    executed_stmt = args[0]
    
    # Check if execution_options dictionary contains timeout=5
    # sqlalchemy Executable/ClauseElement stores options in _execution_options
    assert executed_stmt._execution_options.get("timeout") == 5
