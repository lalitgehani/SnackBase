"""Lexer for rule expressions."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

from .exceptions import RuleSyntaxError

class TokenType(Enum):
    """Types of tokens in rule expressions."""
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    NULL = auto()
    IDENTIFIER = auto()
    
    # Operators
    EQ = auto()  # ==
    NEQ = auto() # !=
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto() # <=
    GTE = auto() # >=
    
    # Logical Operators
    AND = auto()
    OR = auto()
    NOT = auto()
    IN = auto()  # in (membership operator)
    
    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COMMA = auto()
    
    EOF = auto()

@dataclass
class Token:
    """A single token in the rule expression."""
    type: TokenType
    value: str | int | float | bool | None
    position: int

class Lexer:
    """Tokenizes rule strings."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.current_char = self.text[0] if self.text else None

    def error(self, message: str) -> None:
        """Raise a syntax error."""
        raise RuleSyntaxError(message, self.pos)

    def advance(self) -> None:
        """Move one character forward."""
        self.pos += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def peek(self) -> str | None:
        """Look at the next character without moving."""
        peek_pos = self.pos + 1
        return self.text[peek_pos] if peek_pos < len(self.text) else None

    def skip_whitespace(self) -> None:
        """Skip over whitespace characters."""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def _number(self) -> Token:
        """Parse integer or float."""
        start_pos = self.pos
        result = ""
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()

        if self.current_char == ".":
            result += "."
            self.advance()
            while self.current_char is not None and self.current_char.isdigit():
                result += self.current_char
                self.advance()
            return Token(TokenType.FLOAT, float(result), start_pos)
        
        return Token(TokenType.INTEGER, int(result), start_pos)

    def _string(self) -> Token:
        """Parse quoted string."""
        start_pos = self.pos
        quote_char = self.current_char
        self.advance() # Skip opening quote
        
        result = ""
        while self.current_char is not None and self.current_char != quote_char:
            result += self.current_char
            self.advance()
            
        if self.current_char is None:
            self.error("Unterminated string literal")
            
        self.advance() # Skip closing quote
        return Token(TokenType.STRING, result, start_pos)

    def _identifier(self) -> Token:
        """Parse identifier or keyword."""
        start_pos = self.pos
        result = ""
        # Identifiers can invoke letters, numbers, underscores, dots (for variable access), and @ (for macros)
        while self.current_char is not None and (
            self.current_char.isalnum() or self.current_char in "_.@"
        ):
            result += self.current_char
            self.advance()

        # Check for keywords
        if result == "true":
            return Token(TokenType.BOOLEAN, True, start_pos)
        if result == "false":
            return Token(TokenType.BOOLEAN, False, start_pos)
        if result == "null":
            return Token(TokenType.NULL, None, start_pos)
        if result == "and":
            return Token(TokenType.AND, "and", start_pos)
        if result == "or":
            return Token(TokenType.OR, "or", start_pos)
        if result == "not":
            return Token(TokenType.NOT, "not", start_pos)
        if result == "in":
            return Token(TokenType.IN, "in", start_pos)

        return Token(TokenType.IDENTIFIER, result, start_pos)

    def get_next_token(self) -> Token: # noqa: C901
        """Get the next token from input."""
        while self.current_char is not None:

            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char.isdigit():
                return self._number()

            if self.current_char in ("'", '"'):
                return self._string()

            if self.current_char.isalpha() or self.current_char in ("_", "@"):
                return self._identifier()

            start_pos = self.pos

            if self.current_char == "=":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    return Token(TokenType.EQ, "==", start_pos)
                self.error("Unexpected character '='. Did you mean '=='?")

            if self.current_char == "!":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    return Token(TokenType.NEQ, "!=", start_pos)
                self.error("Unexpected character '!'. Did you mean '!='?")
            
            if self.current_char == "<":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    return Token(TokenType.LTE, "<=", start_pos)
                self.advance()
                return Token(TokenType.LT, "<", start_pos)

            if self.current_char == ">":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    return Token(TokenType.GTE, ">=", start_pos)
                self.advance()
                return Token(TokenType.GT, ">", start_pos)

            if self.current_char == "(":
                self.advance()
                return Token(TokenType.LPAREN, "(", start_pos)

            if self.current_char == ")":
                self.advance()
                return Token(TokenType.RPAREN, ")", start_pos)
            
            if self.current_char == ",":
                self.advance()
                return Token(TokenType.COMMA, ",", start_pos)

            if self.current_char == "[":
                self.advance()
                return Token(TokenType.LBRACKET, "[", start_pos)

            if self.current_char == "]":
                self.advance()
                return Token(TokenType.RBRACKET, "]", start_pos)

            self.error(f"Invalid character '{self.current_char}'")

        return Token(TokenType.EOF, None, self.pos)

    def tokenize(self) -> Iterator[Token]:
        """Generator that yields all tokens."""
        while True:
            token = self.get_next_token()
            yield token
            if token.type == TokenType.EOF:
                break
