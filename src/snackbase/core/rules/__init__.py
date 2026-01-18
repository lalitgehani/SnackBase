"""Rule Expression Parser API."""

from .ast import Node
from .exceptions import RuleError, RuleEvaluationError, RuleSyntaxError
from .lexer import Lexer
from .parser import Parser
from .rule_validator import validate_rule_expression
from .sql_compiler import compile_to_sql


def parse_rule(expression: str) -> Node:
    """Parse a rule expression string into an AST."""
    lexer = Lexer(expression)
    parser = Parser(lexer)
    return parser.parse()


__all__ = [
    "parse_rule",
    "compile_to_sql",
    "validate_rule_expression",
    "Node",
    "RuleError",
    "RuleSyntaxError",
    "RuleEvaluationError",
]
