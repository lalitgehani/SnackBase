"""Parser for rule expressions."""

from .ast import BinaryOp, FunctionCall, Literal, Node, UnaryOp, Variable
from .exceptions import RuleSyntaxError
from .lexer import Lexer, Token, TokenType


class Parser:
    """Recursive descent parser for rule expressions."""

    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token: Token = self.lexer.get_next_token()

    def error(self, message: str) -> None:
        """Raise a syntax error."""
        raise RuleSyntaxError(message, self.current_token.position)

    def consume(self, token_type: TokenType) -> None:
        """Consume the current token if it matches the expected type."""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Expected {token_type.name}, found {self.current_token.type.name}")

    def parse(self) -> Node:
        """Parse the entire expression."""
        node = self.expression()
        if self.current_token.type != TokenType.EOF:
            self.error("Unexpected token after expression")
        return node

    def expression(self) -> Node:
        """Parse logical OR expressions."""
        node = self.term()

        while self.current_token.type == TokenType.OR:
            self.consume(TokenType.OR)
            right = self.term()
            node = BinaryOp(left=node, operator="or", right=right)

        return node

    def term(self) -> Node:
        """Parse logical AND expressions."""
        node = self.factor()

        while self.current_token.type == TokenType.AND:
            self.consume(TokenType.AND)
            right = self.factor()
            node = BinaryOp(left=node, operator="and", right=right)

        return node

    def factor(self) -> Node:
        """Parse logical NOT expressions."""
        if self.current_token.type == TokenType.NOT:
            self.consume(TokenType.NOT)
            node = self.factor()
            return UnaryOp(operator="not", operand=node)
        
        return self.comparison()

    def comparison(self) -> Node:
        """Parse comparison expressions."""
        node = self.atom()

        if self.current_token.type in (
            TokenType.EQ, TokenType.NEQ, 
            TokenType.LT, TokenType.GT, 
            TokenType.LTE, TokenType.GTE
        ):
            token = self.current_token
            # Map token type to string operator
            operator_map = {
                TokenType.EQ: "==",
                TokenType.NEQ: "!=",
                TokenType.LT: "<",
                TokenType.GT: ">",
                TokenType.LTE: "<=",
                TokenType.GTE: ">="
            }
            self.consume(token.type)
            right = self.atom()
            node = BinaryOp(left=node, operator=operator_map[token.type], right=right)
        
        return node

    def atom(self) -> Node: # noqa: C901
        """Parse basic units: literals, variables, function calls, parentheses."""
        token = self.current_token

        if token.type == TokenType.INTEGER:
            self.consume(TokenType.INTEGER)
            return Literal(token.value)
        
        if token.type == TokenType.FLOAT:
            self.consume(TokenType.FLOAT)
            return Literal(token.value)
        
        if token.type == TokenType.STRING:
            self.consume(TokenType.STRING)
            return Literal(token.value)
        
        if token.type == TokenType.BOOLEAN:
            self.consume(TokenType.BOOLEAN)
            return Literal(token.value)
        
        if token.type == TokenType.NULL:
            self.consume(TokenType.NULL)
            return Literal(None)

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            node = self.expression()
            self.consume(TokenType.RPAREN)
            return node

        if token.type == TokenType.IDENTIFIER:
            # Check for function call
            # We need to peek to resolve ambiguity between variable and function call
            # But our Lexer doesn't support nice peeking for full tokens easily
            # However, for simplicity, we can consume the identifier and then check if the NEXT token is LPAREN
            
            identifier_value = str(token.value)
            self.consume(TokenType.IDENTIFIER)
            
            if self.current_token.type == TokenType.LPAREN:
                # Function call
                return self._function_call(identifier_value)
            else:
                # Variable
                return Variable(identifier_value)

        self.error(f"Unexpected token: {token.type.name}")
        return Node() # Should not reach here

    def _function_call(self, name: str) -> Node:
        """Parse function call arguments."""
        self.consume(TokenType.LPAREN)
        arguments = []
        
        if self.current_token.type != TokenType.RPAREN:
            arguments.append(self.expression())
            while self.current_token.type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                arguments.append(self.expression())
                
        self.consume(TokenType.RPAREN)
        return FunctionCall(name, arguments)
