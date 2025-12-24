"""Unit tests for Rule Evaluator."""

import pytest
from snackbase.core.rules import evaluate_rule, parse_rule
from snackbase.core.rules.exceptions import RuleEvaluationError


def test_evaluator_literals():
    """Test evaluating constant literals."""
    assert evaluate_rule(parse_rule("true"), {}) is True
    assert evaluate_rule(parse_rule("false"), {}) is False
    assert evaluate_rule(parse_rule("123"), {}) == 123
    assert evaluate_rule(parse_rule("'hello'"), {}) == "hello"
    assert evaluate_rule(parse_rule("null"), {}) is None

def test_evaluator_variables():
    """Test variable resolution."""
    context = {"user": {"id": 1, "role": "admin"}}
    
    assert evaluate_rule(parse_rule("user.id"), context) == 1
    assert evaluate_rule(parse_rule("user.role"), context) == "admin"
    assert evaluate_rule(parse_rule("user.missing"), context) is None
    assert evaluate_rule(parse_rule("missing.variable"), context) is None

def test_evaluator_comparisons():
    """Test comparison operators."""
    context = {"age": 25, "role": "user"}
    
    assert evaluate_rule(parse_rule("age == 25"), context) is True
    assert evaluate_rule(parse_rule("age != 18"), context) is True
    assert evaluate_rule(parse_rule("age > 20"), context) is True
    assert evaluate_rule(parse_rule("age < 30"), context) is True
    assert evaluate_rule(parse_rule("age >= 25"), context) is True
    assert evaluate_rule(parse_rule("age <= 25"), context) is True
    
    # String comparison
    assert evaluate_rule(parse_rule("role == 'user'"), context) is True

def test_evaluator_logic():
    """Test logical operators."""
    context = {"a": True, "b": False}
    
    assert evaluate_rule(parse_rule("a and not b"), context) is True
    assert evaluate_rule(parse_rule("b or a"), context) is True
    assert evaluate_rule(parse_rule("not a"), context) is False

def test_evaluator_functions():
    """Test built-in functions."""
    context = {
        "roles": ["admin", "editor"],
        "email": "user@example.com"
    }
    
    # contains
    assert evaluate_rule(parse_rule("contains(roles, 'admin')"), context) is True
    assert evaluate_rule(parse_rule("contains(roles, 'guest')"), context) is False
    
    # starts_with
    assert evaluate_rule(parse_rule("starts_with(email, 'user')"), context) is True
    assert evaluate_rule(parse_rule("starts_with(email, 'admin')"), context) is False
    
    # ends_with
    assert evaluate_rule(parse_rule("ends_with(email, '@example.com')"), context) is True
    
def test_evaluator_complex_expression():
    """Test a complex real-world rule."""
    expression = """
        (user.role == 'admin') or 
        (user.role == 'editor' and record.status == 'draft') or
        (record.owner_id == user.id)
    """
    
    # Scenario 1: Admin
    ctx1 = {"user": {"role": "admin", "id": 1}, "record": {"status": "published", "owner_id": 2}}
    assert evaluate_rule(parse_rule(expression), ctx1) is True
    
    # Scenario 2: Editor accessing draft
    ctx2 = {"user": {"role": "editor", "id": 2}, "record": {"status": "draft", "owner_id": 3}}
    assert evaluate_rule(parse_rule(expression), ctx2) is True
    
    # Scenario 3: Editor accessing published (fail)
    ctx3 = {"user": {"role": "editor", "id": 2}, "record": {"status": "published", "owner_id": 3}}
    assert evaluate_rule(parse_rule(expression), ctx3) is False
    
    # Scenario 4: User accessing own record
    ctx4 = {"user": {"role": "user", "id": 3}, "record": {"status": "published", "owner_id": 3}}
    assert evaluate_rule(parse_rule(expression), ctx4) is True

def test_evaluator_errors():
    """Test error handling during evaluation."""
    # Type error safety (comparison of incompatible types)
    # Should evaluate to False rather than crash for None types in comparators often
    # But for strict mismatch like int < str it might raise specific py error or handle gracefully
    # Our implementation catches TypeError and returns False
    
    assert evaluate_rule(parse_rule("1 < 'a'"), {}) is False
    
    # Missing function
    with pytest.raises(RuleEvaluationError, match="Unknown function"):
        evaluate_rule(parse_rule("unknown_func()"), {})
