
from unittest.mock import patch
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import patch
from snackbase.core.rules import evaluate_rule, parse_rule
from snackbase.core.rules.evaluator import Evaluator

@dataclass
class UserContext:
    id: int
    role: str
    groups: List[str]
    settings: Optional[dict] = None

def test_macro_has_group():
    """Test @has_group macro."""
    # Dict context
    context = {"user": {"groups": ["admin", "editor"]}}
    assert evaluate_rule(parse_rule("@has_group('admin')"), context) is True
    assert evaluate_rule(parse_rule("@has_group('guest')"), context) is False
    
    # Object context
    user = UserContext(id=1, role="user", groups=["dev"])
    context_obj = {"user": user}
    assert evaluate_rule(parse_rule("@has_group('dev')"), context_obj) is True
    assert evaluate_rule(parse_rule("@has_group('ops')"), context_obj) is False
    
    # Missing user/groups
    assert evaluate_rule(parse_rule("@has_group('admin')"), {}) is False

def test_macro_has_role():
    """Test @has_role macro."""
    # Dict context
    context = {"user": {"role": "admin"}}
    assert evaluate_rule(parse_rule("@has_role('admin')"), context) is True
    assert evaluate_rule(parse_rule("@has_role('user')"), context) is False
    
    # Object context
    user = UserContext(id=1, role="editor", groups=[])
    context_obj = {"user": user}
    assert evaluate_rule(parse_rule("@has_role('editor')"), context_obj) is True
    assert evaluate_rule(parse_rule("@has_role('admin')"), context_obj) is False

def test_macro_owns_record():
    """Test @owns_record and @is_creator macros."""
    # Matching IDs
    context_match = {
        "user": {"id": 10},
        "record": {"owner_id": 10}
    }
    assert evaluate_rule(parse_rule("@owns_record()"), context_match) is True
    assert evaluate_rule(parse_rule("@is_creator()"), context_match) is True
    
    # Mismatching IDs
    context_mismatch = {
        "user": {"id": 10},
        "record": {"owner_id": 20}
    }
    assert evaluate_rule(parse_rule("@owns_record()"), context_mismatch) is False
    
    # Missing data
    assert evaluate_rule(parse_rule("@owns_record()"), {"user": {"id": 1}}) is False
    
    # Dict vs Object mixed
    user_obj = UserContext(id=5, role="user", groups=[])
    rec_ctx = {"owner_id": 5}
    assert evaluate_rule(parse_rule("@owns_record()"), {"user": user_obj, "record": rec_ctx}) is True

def test_macro_in_time_range():
    """Test @in_time_range macro."""
    # Mock datetime to control "now"
    # We need to patch the datetime class in the evaluator module
    # However, since we imported datetime in evaluator, we need to patch 'snackbase.core.rules.evaluator.datetime'
    
    with patch('snackbase.core.rules.evaluator.datetime') as mock_datetime:
        # Case 1: Within range (10:00 is between 9 and 17)
        mock_datetime.now.return_value.hour = 10
        assert evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}) is True
        
        # Case 2: Outside range (18:00 is not between 9 and 17)
        mock_datetime.now.return_value.hour = 18
        assert evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}) is False
        
        # Case 3: Boundary (9:00 IS >= 9)
        mock_datetime.now.return_value.hour = 9
        assert evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}) is True
        
        # Case 4: Boundary (17:00 IS NOT < 17)
        mock_datetime.now.return_value.hour = 17
        assert evaluate_rule(parse_rule("@in_time_range(9, 17)"), {}) is False

def test_macro_has_permission():
    """Test @has_permission macro."""
    context = {
        "permissions": {
            "posts": ["read", "create"],
            "comments": ["read"]
        }
    }
    
    assert evaluate_rule(parse_rule("@has_permission('read', 'posts')"), context) is True
    assert evaluate_rule(parse_rule("@has_permission('delete', 'posts')"), context) is False
    assert evaluate_rule(parse_rule("@has_permission('read', 'comments')"), context) is True
    assert evaluate_rule(parse_rule("@has_permission('read', 'users')"), context) is False
