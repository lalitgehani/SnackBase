"""Parser for rule expressions - SQL-centric syntax."""

from .ast import BinaryOp, FunctionCall, InOp, IsNullOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleSyntaxError
from .lexer import Lexer, Token, TokenType


class Parser:
    """Recursive descent parser for rule expressions with SQL-centric syntax."""

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
        """Parse logical OR expressions (||)."""
        node = self.term()

        while self.current_token.type == TokenType.OR:
            self.consume(TokenType.OR)
            right = self.term()
            node = BinaryOp(left=node, operator="||", right=right)

        return node

    def term(self) -> Node:
        """Parse logical AND expressions (&&)."""
        node = self.factor()

        while self.current_token.type == TokenType.AND:
            self.consume(TokenType.AND)
            right = self.factor()
            node = BinaryOp(left=node, operator="&&", right=right)

        return node

    def factor(self) -> Node:
        """Parse logical NOT expressions (!)."""
        if self.current_token.type == TokenType.NOT:
            self.consume(TokenType.NOT)
            node = self.factor()
            return UnaryOp(operator="!", operand=node)

        return self.comparison()

    def comparison(self) -> Node:
        """Parse comparison expressions (=, !=, <, >, <=, >=, ~, IN, IS NULL, IS NOT NULL)."""
        node = self.additive()

        # Handle IN operator: field IN (val1, val2, ...)
        if self.current_token.type == TokenType.IN:
            self.consume(TokenType.IN)
            self.consume(TokenType.LPAREN)
            values: list[Node] = [self.additive()]
            while self.current_token.type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                values.append(self.additive())
            self.consume(TokenType.RPAREN)
            return InOp(operand=node, values=values)

        # Handle IS NULL / IS NOT NULL
        if self.current_token.type == TokenType.IS:
            self.consume(TokenType.IS)
            if (
                self.current_token.type == TokenType.IDENTIFIER
                and str(self.current_token.value).upper() == "NOT"
            ):
                self.consume(TokenType.IDENTIFIER)  # consume "NOT"
                self.consume(TokenType.NULL)
                return IsNullOp(operand=node, is_null=False)
            self.consume(TokenType.NULL)
            return IsNullOp(operand=node, is_null=True)

        if self.current_token.type in (
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
            TokenType.LIKE,
        ):
            token = self.current_token
            # Map token type to string operator
            operator_map = {
                TokenType.EQ: "=",
                TokenType.NEQ: "!=",
                TokenType.LT: "<",
                TokenType.GT: ">",
                TokenType.LTE: "<=",
                TokenType.GTE: ">=",
                TokenType.LIKE: "~",
            }
            self.consume(token.type)
            right = self.additive()
            node = BinaryOp(left=node, operator=operator_map[token.type], right=right)

        return node

    def additive(self) -> Node:
        """Parse additive expressions (+ and -)."""
        node = self.multiplicative()

        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            token = self.current_token
            op = "+" if token.type == TokenType.PLUS else "-"
            self.consume(token.type)
            right = self.multiplicative()
            node = BinaryOp(left=node, operator=op, right=right)

        return node

    def multiplicative(self) -> Node:
        """Parse multiplicative expressions (*, /, %)."""
        node = self.atom()

        while self.current_token.type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            token = self.current_token
            op_map = {TokenType.STAR: "*", TokenType.SLASH: "/", TokenType.PERCENT: "%"}
            op = op_map[token.type]
            self.consume(token.type)
            right = self.atom()
            node = BinaryOp(left=node, operator=op, right=right)

        return node

    def atom(self) -> Node:
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

        if token.type == TokenType.MINUS:
            # Unary minus: -expr
            self.consume(TokenType.MINUS)
            operand = self.atom()
            return UnaryOp(operator="-", operand=operand)

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            node = self.expression()
            self.consume(TokenType.RPAREN)
            return node

        if token.type == TokenType.IDENTIFIER:
            identifier_value = str(token.value)
            self.consume(TokenType.IDENTIFIER)
            # Check if this is a function call: IDENTIFIER(args...)
            if self.current_token.type == TokenType.LPAREN:
                self.consume(TokenType.LPAREN)
                args: list[Node] = []
                if self.current_token.type != TokenType.RPAREN:
                    args.append(self.expression())
                    while self.current_token.type == TokenType.COMMA:
                        self.consume(TokenType.COMMA)
                        args.append(self.expression())
                self.consume(TokenType.RPAREN)
                return FunctionCall(name=identifier_value, args=args)
            return Variable(identifier_value)

        self.error(f"Unexpected token: {token.type.name}")
        return Node()  # Should not reach here

