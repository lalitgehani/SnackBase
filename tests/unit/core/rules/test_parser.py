"""Tests for SQL-centric rule expression parser."""

import pytest

from snackbase.core.rules.ast import BinaryOp, Literal, UnaryOp, Variable
from snackbase.core.rules.exceptions import RuleSyntaxError
from snackbase.core.rules.lexer import Lexer
from snackbase.core.rules.parser import Parser


class TestParserLiterals:
    """Test parsing literal values."""

    def test_integer(self):
        """Test parsing integer."""
        parser = Parser(Lexer("42"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value == 42

    def test_float(self):
        """Test parsing float."""
        parser = Parser(Lexer("3.14"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value == 3.14

    def test_string(self):
        """Test parsing string."""
        parser = Parser(Lexer("'hello'"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value == "hello"

    def test_boolean_true(self):
        """Test parsing true."""
        parser = Parser(Lexer("true"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value is True

    def test_boolean_false(self):
        """Test parsing false."""
        parser = Parser(Lexer("false"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value is False

    def test_null(self):
        """Test parsing null."""
        parser = Parser(Lexer("null"))
        node = parser.parse()
        assert isinstance(node, Literal)
        assert node.value is None


class TestParserVariables:
    """Test parsing variables."""

    def test_simple_variable(self):
        """Test parsing simple variable."""
        parser = Parser(Lexer("created_by"))
        node = parser.parse()
        assert isinstance(node, Variable)
        assert node.name == "created_by"

    def test_auth_context_variable(self):
        """Test parsing @request.auth.* variable."""
        parser = Parser(Lexer("@request.auth.id"))
        node = parser.parse()
        assert isinstance(node, Variable)
        assert node.name == "@request.auth.id"

    def test_data_context_variable(self):
        """Test parsing @request.data.* variable."""
        parser = Parser(Lexer("@request.data.title"))
        node = parser.parse()
        assert isinstance(node, Variable)
        assert node.name == "@request.data.title"


class TestParserComparisons:
    """Test parsing comparison expressions."""

    def test_equals(self):
        """Test parsing = comparison."""
        parser = Parser(Lexer("created_by = @request.auth.id"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "="
        assert isinstance(node.left, Variable)
        assert node.left.name == "created_by"
        assert isinstance(node.right, Variable)
        assert node.right.name == "@request.auth.id"

    def test_not_equals(self):
        """Test parsing != comparison."""
        parser = Parser(Lexer("status != 'draft'"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "!="

    def test_less_than(self):
        """Test parsing < comparison."""
        parser = Parser(Lexer("age < 18"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "<"

    def test_greater_than(self):
        """Test parsing > comparison."""
        parser = Parser(Lexer("age > 18"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == ">"

    def test_less_than_or_equal(self):
        """Test parsing <= comparison."""
        parser = Parser(Lexer("age <= 18"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "<="

    def test_greater_than_or_equal(self):
        """Test parsing >= comparison."""
        parser = Parser(Lexer("age >= 18"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == ">="

    def test_like(self):
        """Test parsing ~ (LIKE) comparison."""
        parser = Parser(Lexer("name ~ 'John%'"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "~"


class TestParserLogicalOperators:
    """Test parsing logical operators."""

    def test_and(self):
        """Test parsing && operator."""
        parser = Parser(Lexer("created_by = @request.auth.id && status = 'published'"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "&&"
        assert isinstance(node.left, BinaryOp)
        assert isinstance(node.right, BinaryOp)

    def test_or(self):
        """Test parsing || operator."""
        parser = Parser(Lexer("public = true || created_by = @request.auth.id"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "||"

    def test_not(self):
        """Test parsing ! operator."""
        parser = Parser(Lexer("!(status = 'draft')"))
        node = parser.parse()
        assert isinstance(node, UnaryOp)
        assert node.operator == "!"
        assert isinstance(node.operand, BinaryOp)


class TestParserPrecedence:
    """Test operator precedence."""

    def test_and_before_or(self):
        """Test that && has higher precedence than ||."""
        parser = Parser(Lexer("a = 1 || b = 2 && c = 3"))
        node = parser.parse()
        # Should parse as: a = 1 || (b = 2 && c = 3)
        assert isinstance(node, BinaryOp)
        assert node.operator == "||"
        assert isinstance(node.right, BinaryOp)
        assert node.right.operator == "&&"

    def test_not_before_and(self):
        """Test that ! has higher precedence than &&."""
        parser = Parser(Lexer("!(a = 1) && b = 2"))
        node = parser.parse()
        # Should parse as: (!(a = 1)) && (b = 2)
        assert isinstance(node, BinaryOp)
        assert node.operator == "&&"
        assert isinstance(node.left, UnaryOp)  # Fixed: NOT wraps the comparison
        assert isinstance(node.left.operand, BinaryOp)


class TestParserParentheses:
    """Test parsing expressions with parentheses."""

    def test_simple_parentheses(self):
        """Test parsing simple parentheses."""
        parser = Parser(Lexer("(status = 'draft')"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "="

    def test_parentheses_change_precedence(self):
        """Test that parentheses change precedence."""
        parser = Parser(Lexer("(a = 1 || b = 2) && c = 3"))
        node = parser.parse()
        # Should parse as: (a = 1 || b = 2) && c = 3
        assert isinstance(node, BinaryOp)
        assert node.operator == "&&"
        assert isinstance(node.left, BinaryOp)
        assert node.left.operator == "||"

    def test_nested_parentheses(self):
        """Test parsing nested parentheses."""
        parser = Parser(Lexer("((a = 1))"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "="


class TestParserComplexExpressions:
    """Test parsing complex expressions."""

    def test_ownership_rule(self):
        """Test parsing ownership rule."""
        parser = Parser(Lexer("created_by = @request.auth.id"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "="
        assert node.left.name == "created_by"
        assert node.right.name == "@request.auth.id"

    def test_ownership_or_public(self):
        """Test parsing ownership or public rule."""
        parser = Parser(Lexer("created_by = @request.auth.id || public = true"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "||"

    def test_account_isolation(self):
        """Test parsing account isolation rule."""
        parser = Parser(Lexer("account_id = @request.auth.account_id"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "="
        assert node.left.name == "account_id"
        assert node.right.name == "@request.auth.account_id"

    def test_complex_multi_condition(self):
        """Test parsing complex multi-condition rule."""
        parser = Parser(
            Lexer(
                "created_by = @request.auth.id && status = 'published' && account_id = @request.auth.account_id"
            )
        )
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "&&"

    def test_request_data_validation(self):
        """Test parsing @request.data.* in create rule."""
        parser = Parser(Lexer("@request.data.title != ''"))
        node = parser.parse()
        assert isinstance(node, BinaryOp)
        assert node.operator == "!="
        assert node.left.name == "@request.data.title"


class TestParserErrors:
    """Test parser error handling."""

    def test_unexpected_token(self):
        """Test error on unexpected token."""
        parser = Parser(Lexer("created_by ="))
        with pytest.raises(RuleSyntaxError):
            parser.parse()

    def test_missing_closing_paren(self):
        """Test error on missing closing parenthesis."""
        parser = Parser(Lexer("(status = 'draft'"))
        with pytest.raises(RuleSyntaxError):
            parser.parse()

    def test_extra_tokens(self):
        """Test error on extra tokens after expression."""
        parser = Parser(Lexer("status = 'draft' extra"))
        with pytest.raises(RuleSyntaxError, match="Unexpected token after expression"):
            parser.parse()
