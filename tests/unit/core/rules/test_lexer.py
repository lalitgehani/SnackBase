"""Tests for SQL-centric rule expression lexer."""

import pytest

from snackbase.core.rules.exceptions import RuleSyntaxError
from snackbase.core.rules.lexer import Lexer, TokenType


class TestLexerBasics:
    """Test basic lexer functionality."""

    def test_empty_string(self):
        """Test lexing empty string."""
        lexer = Lexer("")
        token = lexer.get_next_token()
        assert token.type == TokenType.EOF

    def test_whitespace_only(self):
        """Test lexing whitespace."""
        lexer = Lexer("   \t\n  ")
        token = lexer.get_next_token()
        assert token.type == TokenType.EOF


class TestLexerLiterals:
    """Test lexing literal values."""

    def test_integer(self):
        """Test lexing integers."""
        lexer = Lexer("42")
        token = lexer.get_next_token()
        assert token.type == TokenType.INTEGER
        assert token.value == 42

    def test_float(self):
        """Test lexing floats."""
        lexer = Lexer("3.14")
        token = lexer.get_next_token()
        assert token.type == TokenType.FLOAT
        assert token.value == 3.14

    def test_string_single_quotes(self):
        """Test lexing single-quoted strings."""
        lexer = Lexer("'hello world'")
        token = lexer.get_next_token()
        assert token.type == TokenType.STRING
        assert token.value == "hello world"

    def test_string_double_quotes(self):
        """Test lexing double-quoted strings."""
        lexer = Lexer('"hello world"')
        token = lexer.get_next_token()
        assert token.type == TokenType.STRING
        assert token.value == "hello world"

    def test_string_with_escapes(self):
        """Test lexing strings with escape sequences."""
        lexer = Lexer(r'"hello \"world\""')
        token = lexer.get_next_token()
        assert token.type == TokenType.STRING
        assert token.value == 'hello "world"'

    def test_boolean_true(self):
        """Test lexing true."""
        lexer = Lexer("true")
        token = lexer.get_next_token()
        assert token.type == TokenType.BOOLEAN
        assert token.value is True

    def test_boolean_false(self):
        """Test lexing false."""
        lexer = Lexer("false")
        token = lexer.get_next_token()
        assert token.type == TokenType.BOOLEAN
        assert token.value is False

    def test_null(self):
        """Test lexing null."""
        lexer = Lexer("null")
        token = lexer.get_next_token()
        assert token.type == TokenType.NULL
        assert token.value is None


class TestLexerOperators:
    """Test lexing SQL-centric operators."""

    def test_equals(self):
        """Test lexing = operator."""
        lexer = Lexer("=")
        token = lexer.get_next_token()
        assert token.type == TokenType.EQ
        assert token.value == "="

    def test_not_equals(self):
        """Test lexing != operator."""
        lexer = Lexer("!=")
        token = lexer.get_next_token()
        assert token.type == TokenType.NEQ
        assert token.value == "!="

    def test_less_than(self):
        """Test lexing < operator."""
        lexer = Lexer("<")
        token = lexer.get_next_token()
        assert token.type == TokenType.LT
        assert token.value == "<"

    def test_greater_than(self):
        """Test lexing > operator."""
        lexer = Lexer(">")
        token = lexer.get_next_token()
        assert token.type == TokenType.GT
        assert token.value == ">"

    def test_less_than_or_equal(self):
        """Test lexing <= operator."""
        lexer = Lexer("<=")
        token = lexer.get_next_token()
        assert token.type == TokenType.LTE
        assert token.value == "<="

    def test_greater_than_or_equal(self):
        """Test lexing >= operator."""
        lexer = Lexer(">=")
        token = lexer.get_next_token()
        assert token.type == TokenType.GTE
        assert token.value == ">="

    def test_like(self):
        """Test lexing ~ (LIKE) operator."""
        lexer = Lexer("~")
        token = lexer.get_next_token()
        assert token.type == TokenType.LIKE
        assert token.value == "~"

    def test_and(self):
        """Test lexing && operator."""
        lexer = Lexer("&&")
        token = lexer.get_next_token()
        assert token.type == TokenType.AND
        assert token.value == "&&"

    def test_or(self):
        """Test lexing || operator."""
        lexer = Lexer("||")
        token = lexer.get_next_token()
        assert token.type == TokenType.OR
        assert token.value == "||"

    def test_not(self):
        """Test lexing ! operator."""
        lexer = Lexer("!")
        token = lexer.get_next_token()
        assert token.type == TokenType.NOT
        assert token.value == "!"


class TestLexerIdentifiers:
    """Test lexing identifiers and context variables."""

    def test_simple_identifier(self):
        """Test lexing simple identifier."""
        lexer = Lexer("created_by")
        token = lexer.get_next_token()
        assert token.type == TokenType.IDENTIFIER
        assert token.value == "created_by"

    def test_auth_context_variable(self):
        """Test lexing @request.auth.* variable."""
        lexer = Lexer("@request.auth.id")
        token = lexer.get_next_token()
        assert token.type == TokenType.IDENTIFIER
        assert token.value == "@request.auth.id"

    def test_data_context_variable(self):
        """Test lexing @request.data.* variable."""
        lexer = Lexer("@request.data.title")
        token = lexer.get_next_token()
        assert token.type == TokenType.IDENTIFIER
        assert token.value == "@request.data.title"


class TestLexerExpressions:
    """Test lexing complete expressions."""

    def test_simple_comparison(self):
        """Test lexing simple comparison."""
        lexer = Lexer("created_by = @request.auth.id")
        tokens = list(lexer.tokenize())

        assert len(tokens) == 4  # identifier, =, identifier, EOF
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "created_by"
        assert tokens[1].type == TokenType.EQ
        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "@request.auth.id"
        assert tokens[3].type == TokenType.EOF

    def test_complex_expression(self):
        """Test lexing complex expression with AND."""
        lexer = Lexer("created_by = @request.auth.id && status = 'published'")
        tokens = list(lexer.tokenize())

        assert tokens[0].value == "created_by"
        assert tokens[1].type == TokenType.EQ
        assert tokens[2].value == "@request.auth.id"
        assert tokens[3].type == TokenType.AND
        assert tokens[4].value == "status"
        assert tokens[5].type == TokenType.EQ
        assert tokens[6].value == "published"
        assert tokens[7].type == TokenType.EOF

    def test_expression_with_parentheses(self):
        """Test lexing expression with parentheses."""
        lexer = Lexer("(status = 'draft' || status = 'published')")
        tokens = list(lexer.tokenize())

        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].value == "status"
        assert tokens[4].type == TokenType.OR
        assert tokens[8].type == TokenType.RPAREN  # Fixed: was tokens[7]

    def test_like_expression(self):
        """Test lexing LIKE expression."""
        lexer = Lexer("name ~ 'John%'")
        tokens = list(lexer.tokenize())

        assert tokens[0].value == "name"
        assert tokens[1].type == TokenType.LIKE
        assert tokens[2].value == "John%"


class TestLexerErrors:
    """Test lexer error handling."""

    def test_unterminated_string(self):
        """Test error on unterminated string."""
        lexer = Lexer("'hello")
        with pytest.raises(RuleSyntaxError, match="Unterminated string literal"):
            lexer.get_next_token()

    def test_invalid_character(self):
        """Test error on invalid character."""
        lexer = Lexer("$invalid")
        with pytest.raises(RuleSyntaxError, match="Invalid character"):
            lexer.get_next_token()

    def test_single_ampersand(self):
        """Test error on single &."""
        lexer = Lexer("a & b")
        with pytest.raises(RuleSyntaxError, match="Did you mean '\u0026\u0026'"):
            list(lexer.tokenize())

    def test_single_pipe(self):
        """Test error on single |."""
        lexer = Lexer("a | b")
        with pytest.raises(RuleSyntaxError, match="Did you mean '\\|\\|'"):
            list(lexer.tokenize())
