"""Integration tests for Evaluator with Macros."""

import json
import pytest
from sqlalchemy import text
from snackbase.core.rules import evaluate_rule, parse_rule
from snackbase.core.macros.engine import MacroExecutionEngine
from snackbase.infrastructure.persistence.models.macro import MacroModel
from snackbase.infrastructure.persistence.repositories.macro_repository import MacroRepository

# Assuming there is a fixture for async_session available in integration tests.
# Since I cannot find conftest.py, I will try to rely on typical pytest-asyncio plugins or 
# assume a `db_session` fixture exists if other integration tests use it.
# However, if I cannot find it, I might fail.
# Let's try to infer from finding files in integration folder.

@pytest.mark.asyncio
async def test_integration_sql_macro(db_session):
    """Test full integration of SQL macro execution."""
    # 1. Setup: Create a macro in DB
    repo = MacroRepository(db_session)
    macro_name = "is_active_user"
    sql = "SELECT CASE WHEN :status = 'active' THEN 1 ELSE 0 END"
    
    await repo.create(
        name=macro_name,
        sql_query=sql,
        parameters=["status"]
    )
    
    # 2. Setup: Init Engine and Evaluator
    engine = MacroExecutionEngine(db_session)
    
    # 3. Evaluate Rule
    context = {"user": {"status": "active"}}
    rule_str = "@is_active_user(user.status) == 1"
    
    result = await evaluate_rule(parse_rule(rule_str), context, engine)
    assert result is True
    
    # Test false case
    context_inactive = {"user": {"status": "inactive"}}
    result_false = await evaluate_rule(parse_rule(rule_str), context_inactive, engine)
    assert result_false is False
    
    # Cleanup (optional if transaction rollback is used by fixture)
    
