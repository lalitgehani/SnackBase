
import pytest
from unittest.mock import patch
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import patch
from snackbase.core.rules import evaluate_rule, parse_rule
from snackbase.core.rules.evaluator import Evaluator
from snackbase.core.macros.engine import MacroExecutionEngine

@dataclass
class UserContext:
    id: int
    role: str
    groups: List[str]
    settings: Optional[dict] = None

engine = MacroExecutionEngine()

@pytest.mark.asyncio
async def test_macro_has_group():
    """Test @has_group macro."""
    # Dict context
    context = {"user": {"groups": ["admin", "editor"]}}
    assert await evaluate_rule(parse_rule("@has_group('admin')"), context, engine) is True
    assert await evaluate_rule(parse_rule("@has_group('guest')"), context, engine) is False
    
    # Object context
    user = UserContext(id=1, role="user", groups=["dev"])
    context_obj = {"user": user}
    assert await evaluate_rule(parse_rule("@has_group('dev')"), context_obj, engine) is True
    assert await evaluate_rule(parse_rule("@has_group('ops')"), context_obj, engine) is False
    
    # Missing user/groups
    assert await evaluate_rule(parse_rule("@has_group('admin')"), {}, engine) is False

@pytest.mark.asyncio
async def test_macro_has_role():
    """Test @has_role macro."""
    # Dict context
    context = {"user": {"role": "admin"}}
    assert await evaluate_rule(parse_rule("@has_role('admin')"), context, engine) is True
    assert await evaluate_rule(parse_rule("@has_role('user')"), context, engine) is False
    
    # Object context
    user = UserContext(id=1, role="editor", groups=[])
    context_obj = {"user": user}
    assert await evaluate_rule(parse_rule("@has_role('editor')"), context_obj, engine) is True
    assert await evaluate_rule(parse_rule("@has_role('admin')"), context_obj, engine) is False

@pytest.mark.asyncio
async def test_macro_owns_record():
    """Test @owns_record and @is_creator macros."""
    # Matching IDs
    context_match = {
        "user": {"id": 10},
        "record": {"owner_id": 10}
    }
    assert await evaluate_rule(parse_rule("@owns_record()"), context_match, engine) is True
    assert await evaluate_rule(parse_rule("@is_creator()"), context_match, engine) is True
    
    # Mismatching IDs
    context_mismatch = {
        "user": {"id": 10},
        "record": {"owner_id": 20}
    }
    assert await evaluate_rule(parse_rule("@owns_record()"), context_mismatch, engine) is False
    
    # Missing data
    assert await evaluate_rule(parse_rule("@owns_record()"), {"user": {"id": 1}}, engine) is False
    
    # Dict vs Object mixed
    user_obj = UserContext(id=5, role="user", groups=[])
    rec_ctx = {"owner_id": 5}
    assert await evaluate_rule(parse_rule("@owns_record()"), {"user": user_obj, "record": rec_ctx}, engine) is True

@pytest.mark.asyncio
async def test_macro_in_time_range():
    """Test @in_time_range macro."""
    # We need to patch datetime.datetime directly because the import is local
    # mocking the datetime module where it's used is tricky with local imports
    # so we patch the builtin datetime class.
    # Note: Patching built-in C types can be tricky, but let's try wrapping via SafePatch if needed,
    # or just patch 'datetime.datetime' which works in most python envs if not restricted.
    
    import datetime
    
    # Create a mock class that behaves like datetime
    class MockDateTime(datetime.datetime):
        @classmethod
        def now(cls):
            return cls._now_val

    MockDateTime._now_val = datetime.datetime(2023, 1, 1, 10, 0, 0) # Default 10:00

    with patch('datetime.datetime', MockDateTime):
        # Case 1: Within range (10:00 is between 9 and 17)
        MockDateTime._now_val = datetime.datetime(2023, 1, 1, 10, 0, 0)
        assert await evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}, engine) is True
        
        # Case 2: Outside range (18:00 is not between 9 and 17)
        MockDateTime._now_val = datetime.datetime(2023, 1, 1, 18, 0, 0)
        assert await evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}, engine) is False
        
        # Case 3: Boundary (9:00 IS >= 9)
        MockDateTime._now_val = datetime.datetime(2023, 1, 1, 9, 0, 0)
        assert await evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}, engine) is True
        
        # Case 4: Boundary (17:00 IS NOT < 17)
        MockDateTime._now_val = datetime.datetime(2023, 1, 1, 17, 0, 0)
        assert await evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}, engine) is False

@pytest.mark.asyncio
async def test_macro_has_permission():
    """Test @has_permission macro."""
    context = {
        "permissions": {
            "posts": ["read", "create"],
            "comments": ["read"]
        }
    }
    
    assert await evaluate_rule(parse_rule("@has_permission('read', 'posts')"), context, engine) is True
    assert await evaluate_rule(parse_rule("@has_permission('delete', 'posts')"), context, engine) is False
    assert await evaluate_rule(parse_rule("@has_permission('read', 'comments')"), context, engine) is True
    assert await evaluate_rule(parse_rule("@has_permission('read', 'users')"), context, engine) is False
