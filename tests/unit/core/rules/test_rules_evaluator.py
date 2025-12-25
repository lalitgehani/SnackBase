"""Unit tests for Rule Evaluator."""

import pytest
from dataclasses import dataclass
from typing import Optional, List
from snackbase.core.rules import evaluate_rule, parse_rule
from snackbase.core.rules.exceptions import RuleEvaluationError

@dataclass
class UserContext:
    id: int
    role: str
    groups: List[str]
    settings: Optional[dict] = None

@dataclass
class RecordContext:
    owner_id: int
    status: str

@pytest.mark.asyncio
async def test_evaluator_literals():
    """Test evaluating constant literals."""
    assert await evaluate_rule(parse_rule("true"), {}) is True
    assert await evaluate_rule(parse_rule("false"), {}) is False
    assert await evaluate_rule(parse_rule("123"), {}) == 123
    assert await evaluate_rule(parse_rule("'hello'"), {}) == "hello"
    assert await evaluate_rule(parse_rule("null"), {}) is None

@pytest.mark.asyncio
async def test_evaluator_variables_dict():
    """Test variable resolution with dictionary context."""
    context = {"user": {"id": 1, "role": "admin"}}
    
    assert await evaluate_rule(parse_rule("user.id"), context) == 1
    assert await evaluate_rule(parse_rule("user.role"), context) == "admin"
    assert await evaluate_rule(parse_rule("user.missing"), context) is None
    assert await evaluate_rule(parse_rule("missing.variable"), context) is None

@pytest.mark.asyncio
async def test_evaluator_variables_objects():
    """Test variable resolution with object context."""
    user = UserContext(id=1, role="admin", groups=["dev", "ops"], settings={"theme": "dark"})
    context = {"user": user}
    
    assert await evaluate_rule(parse_rule("user.id"), context) == 1
    assert await evaluate_rule(parse_rule("user.role"), context) == "admin"
    assert await evaluate_rule(parse_rule("user.settings.theme"), context) == "dark"
    # Accessing missing attribute should return None safely
    assert await evaluate_rule(parse_rule("user.missing_attr"), context) is None
    
@pytest.mark.asyncio
async def test_evaluator_comparisons():
    """Test comparison operators."""
    context = {"age": 25, "role": "user"}
    
    assert await evaluate_rule(parse_rule("age == 25"), context) is True
    assert await evaluate_rule(parse_rule("age != 18"), context) is True
    assert await evaluate_rule(parse_rule("age > 20"), context) is True
    assert await evaluate_rule(parse_rule("age < 30"), context) is True
    assert await evaluate_rule(parse_rule("age >= 25"), context) is True
    assert await evaluate_rule(parse_rule("age <= 25"), context) is True
    
    # String comparison
    assert await evaluate_rule(parse_rule("role == 'user'"), context) is True

@pytest.mark.asyncio
async def test_evaluator_logic_short_circuit():
    """Test logical operators with short-circuiting."""
    context = {"a": True, "b": False}
    
    # Simple logic
    assert await evaluate_rule(parse_rule("a and not b"), context) is True
    assert await evaluate_rule(parse_rule("b or a"), context) is True
    
    # Short-circuiting:
    # 'a' is True, so 'a or <error>' should be True without evaluating <error>
    # creating a mock object that raises error on access to simulate dangerous op
    class Dangerous:
        @property
        def boom(self):
            raise RuntimeError("Should not be called")
            
    context_danger = {"a": True, "d": Dangerous()}
    # If short-circuit works, d.boom is never accessed
    assert await evaluate_rule(parse_rule("a or d.boom"), context_danger) is True
    
    context_danger_false = {"b": False, "d": Dangerous()}
    # If short-circuit works, d.boom is never accessed for AND if first is False
    assert await evaluate_rule(parse_rule("b and d.boom"), context_danger_false) is False

@pytest.mark.asyncio
async def test_evaluator_functions():
    """Test built-in functions."""
    context = {
        "roles": ["admin", "editor"],
        "email": "user@example.com"
    }
    
    # contains
    assert await evaluate_rule(parse_rule("contains(roles, 'admin')"), context) is True
    assert await evaluate_rule(parse_rule("contains(roles, 'guest')"), context) is False
    
    # starts_with
    assert await evaluate_rule(parse_rule("starts_with(email, 'user')"), context) is True
    assert await evaluate_rule(parse_rule("starts_with(email, 'admin')"), context) is False
    
    # ends_with
    assert await evaluate_rule(parse_rule("ends_with(email, '@example.com')"), context) is True
    
@pytest.mark.asyncio
async def test_evaluator_complex_expression():
    """Test a complex real-world rule."""
    expression = """
        (user.role == 'admin') or 
        (user.role == 'editor' and record.status == 'draft') or
        (record.owner_id == user.id)
    """
    
    # Scenario 1: Admin
    ctx1 = {"user": {"role": "admin", "id": 1}, "record": {"status": "published", "owner_id": 2}}
    assert await evaluate_rule(parse_rule(expression), ctx1) is True
    
    # Scenario 2: Editor accessing draft
    ctx2 = {"user": {"role": "editor", "id": 2}, "record": {"status": "draft", "owner_id": 3}}
    assert await evaluate_rule(parse_rule(expression), ctx2) is True
    
    # Scenario 3: Editor accessing published (fail)
    ctx3 = {"user": {"role": "editor", "id": 2}, "record": {"status": "published", "owner_id": 3}}
    assert await evaluate_rule(parse_rule(expression), ctx3) is False
    
    # Scenario 4: User accessing own record
    ctx4 = {"user": {"role": "user", "id": 3}, "record": {"status": "published", "owner_id": 3}}
    assert await evaluate_rule(parse_rule(expression), ctx4) is True

@pytest.mark.asyncio
async def test_evaluator_errors():
    """Test error handling during evaluation."""
    # Type error safety (comparison of incompatible types)
    assert await evaluate_rule(parse_rule("1 < 'a'"), {}) is False
    
    # Missing function
    with pytest.raises(RuleEvaluationError, match="Unknown function"):
        await evaluate_rule(parse_rule("unknown_func()"), {})


@pytest.mark.asyncio
async def test_evaluator_in_operator_with_list_literal():
    """Test 'in' operator with inline list literals."""
    # Simple string in list
    assert await evaluate_rule(parse_rule("'admin' in ['admin', 'user']"), {}) is True
    assert await evaluate_rule(parse_rule("'guest' in ['admin', 'user']"), {}) is False
    
    # Integer in list
    assert await evaluate_rule(parse_rule("1 in [1, 2, 3]"), {}) is True
    assert await evaluate_rule(parse_rule("5 in [1, 2, 3]"), {}) is False


@pytest.mark.asyncio
async def test_evaluator_in_operator_with_variable():
    """Test 'in' operator with variable on left side."""
    context = {"user": {"id": "user123", "role": "admin"}}
    
    # Variable in list
    assert await evaluate_rule(parse_rule("user.id in ['user123', 'user456']"), context) is True
    assert await evaluate_rule(parse_rule("user.id in ['user456', 'user789']"), context) is False
    
    # Role check
    assert await evaluate_rule(parse_rule("user.role in ['admin', 'superadmin']"), context) is True
    assert await evaluate_rule(parse_rule("user.role in ['editor', 'viewer']"), context) is False


@pytest.mark.asyncio
async def test_evaluator_in_operator_with_array_variable():
    """Test 'in' operator with array variable on right side."""
    context = {"allowed_users": ["user1", "user2", "user3"], "current_user": "user2"}
    
    assert await evaluate_rule(parse_rule("current_user in allowed_users"), context) is True
    
    context["current_user"] = "user5"
    assert await evaluate_rule(parse_rule("current_user in allowed_users"), context) is False


@pytest.mark.asyncio
async def test_evaluator_in_operator_null_handling():
    """Test 'in' operator with null values."""
    context = {"user": {"id": None}, "items": None}
    
    # Null in list should work
    assert await evaluate_rule(parse_rule("user.id in [null, 'a']"), context) is True
    
    # Value in null collection should return False
    assert await evaluate_rule(parse_rule("'a' in items"), context) is False


@pytest.mark.asyncio
async def test_evaluator_user_specific_rule():
    """Test user-specific permission rule: user.id == 'specific_user'."""
    # User-specific rule with exact match
    rule = "user.id == 'user_abc123'"
    
    ctx_match = {"user": {"id": "user_abc123"}}
    ctx_no_match = {"user": {"id": "user_xyz789"}}
    
    assert await evaluate_rule(parse_rule(rule), ctx_match) is True
    assert await evaluate_rule(parse_rule(rule), ctx_no_match) is False


@pytest.mark.asyncio
async def test_evaluator_user_specific_rule_combined_with_role():
    """Test user-specific rule combined with role rule using OR."""
    # User-specific or role-based access
    rule = "user.id == 'special_user' or user.role == 'admin'"
    
    # Special user (any role)
    ctx1 = {"user": {"id": "special_user", "role": "viewer"}}
    assert await evaluate_rule(parse_rule(rule), ctx1) is True
    
    # Admin (any user)
    ctx2 = {"user": {"id": "regular_user", "role": "admin"}}
    assert await evaluate_rule(parse_rule(rule), ctx2) is True
    
    # Neither special user nor admin
    ctx3 = {"user": {"id": "regular_user", "role": "viewer"}}
    assert await evaluate_rule(parse_rule(rule), ctx3) is False


@pytest.mark.asyncio
async def test_evaluator_multiple_users_in_array():
    """Test granting access to multiple specific users: user.id in ['user1', 'user2']."""
    rule = "user.id in ['user1', 'user2', 'user3']"
    
    assert await evaluate_rule(parse_rule(rule), {"user": {"id": "user1"}}) is True
    assert await evaluate_rule(parse_rule(rule), {"user": {"id": "user2"}}) is True
    assert await evaluate_rule(parse_rule(rule), {"user": {"id": "user3"}}) is True
    assert await evaluate_rule(parse_rule(rule), {"user": {"id": "user4"}}) is False
