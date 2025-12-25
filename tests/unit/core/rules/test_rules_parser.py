"""Unit tests for Rule Parser and Lexer."""

import pytest
from snackbase.core.rules.ast import BinaryOp, FunctionCall, Literal, UnaryOp, Variable
from snackbase.core.rules.exceptions import RuleSyntaxError
from snackbase.core.rules.lexer import Lexer, TokenType
from snackbase.core.rules.parser import Parser


def test_lexer_tokens():
    """Test basic tokenization."""
    lexer = Lexer('user.id == 123 and "admin" != null')
    tokens = list(lexer.tokenize())
    
    expected_types = [
        TokenType.IDENTIFIER, TokenType.EQ, TokenType.INTEGER,
        TokenType.AND, TokenType.STRING, TokenType.NEQ, TokenType.NULL,
        TokenType.EOF
    ]
    
    assert len(tokens) == len(expected_types)
    for i, token in enumerate(tokens):
        assert token.type == expected_types[i]

def test_lexer_identifiers_and_keywords():
    """Test identifiers and keywords."""
    lexer = Lexer('true false null and or not user.email')
    tokens = list(lexer.tokenize())
    
    assert tokens[0].type == TokenType.BOOLEAN
    assert tokens[0].value is True
    assert tokens[1].type == TokenType.BOOLEAN
    assert tokens[1].value is False
    assert tokens[2].type == TokenType.NULL
    assert tokens[2].value is None
    assert tokens[3].type == TokenType.AND
    assert tokens[4].type == TokenType.OR
    assert tokens[5].type == TokenType.NOT
    assert tokens[6].type == TokenType.IDENTIFIER
    assert tokens[6].value == "user.email"

def test_parser_binary_ops():
    """Test parsing binary operations."""
    lexer = Lexer("a == b")
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, BinaryOp)
    assert node.operator == "=="
    assert isinstance(node.left, Variable)
    assert node.left.name == "a"
    assert isinstance(node.right, Variable)
    assert node.right.name == "b"

def test_parser_precedence():
    """Test operator precedence."""
    # not > and > or
    lexer = Lexer("not a or b and c")
    parser = Parser(lexer)
    node = parser.parse()
    
    # Structure should be: (not a) or (b and c)
    assert isinstance(node, BinaryOp)
    assert node.operator == "or"
    
    assert isinstance(node.left, UnaryOp)
    assert node.left.operator == "not"
    
    assert isinstance(node.right, BinaryOp)
    assert node.right.operator == "and"

def test_parser_grouping():
    """Test parentheses grouping."""
    lexer = Lexer("(a or b) and c")
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, BinaryOp)
    assert node.operator == "and"
    
    assert isinstance(node.left, BinaryOp)
    assert node.left.operator == "or"
    assert isinstance(node.left.left, Variable)
    assert node.left.left.name == "a"

def test_parser_function_call():
    """Test function calls."""
    lexer = Lexer('contains(user.roles, "admin")')
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, FunctionCall)
    assert node.name == "contains"
    assert len(node.arguments) == 2
    assert isinstance(node.arguments[0], Variable)
    assert node.arguments[0].name == "user.roles"
    assert isinstance(node.arguments[1], Literal)
    assert node.arguments[1].value == "admin"

def test_parser_syntax_error():
    """Test syntax error handling."""
    with pytest.raises(RuleSyntaxError, match="Unexpected token"):
        lexer = Lexer("user.id ==") # Missing right operand, will hit EOF unexpectedly or error
        parser = Parser(lexer)
        parser.parse()

def test_parser_invalid_token():
    """Test invalid token error."""
    with pytest.raises(RuleSyntaxError):
        lexer = Lexer("user.id # 1") # # is invalid
        list(lexer.tokenize())


def test_lexer_in_keyword():
    """Test 'in' keyword tokenization."""
    lexer = Lexer("user.id in ['admin', 'user']")
    tokens = list(lexer.tokenize())
    
    expected_types = [
        TokenType.IDENTIFIER, TokenType.IN, TokenType.LBRACKET,
        TokenType.STRING, TokenType.COMMA, TokenType.STRING,
        TokenType.RBRACKET, TokenType.EOF
    ]
    
    assert len(tokens) == len(expected_types)
    for i, token in enumerate(tokens):
        assert token.type == expected_types[i], f"Token {i}: expected {expected_types[i]}, got {token.type}"


def test_lexer_brackets():
    """Test bracket tokenization."""
    lexer = Lexer("[]")
    tokens = list(lexer.tokenize())
    
    assert tokens[0].type == TokenType.LBRACKET
    assert tokens[1].type == TokenType.RBRACKET


def test_parser_in_operator():
    """Test parsing 'in' operator with list literal."""
    from snackbase.core.rules.ast import ListLiteral
    
    lexer = Lexer("user.id in ['admin', 'user']")
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, BinaryOp)
    assert node.operator == "in"
    assert isinstance(node.left, Variable)
    assert node.left.name == "user.id"
    assert isinstance(node.right, ListLiteral)
    assert len(node.right.items) == 2
    assert isinstance(node.right.items[0], Literal)
    assert node.right.items[0].value == "admin"
    assert node.right.items[1].value == "user"


def test_parser_empty_list():
    """Test parsing empty list literal."""
    from snackbase.core.rules.ast import ListLiteral
    
    lexer = Lexer("[]")
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, ListLiteral)
    assert len(node.items) == 0


def test_parser_list_with_expressions():
    """Test parsing list literal with expressions."""
    from snackbase.core.rules.ast import ListLiteral
    
    lexer = Lexer("[1, 2, 'three', true]")
    parser = Parser(lexer)
    node = parser.parse()
    
    assert isinstance(node, ListLiteral)
    assert len(node.items) == 4
    assert node.items[0].value == 1
    assert node.items[1].value == 2
    assert node.items[2].value == "three"
    assert node.items[3].value is True
