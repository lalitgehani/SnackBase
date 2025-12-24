"""Rule Expression Parser API."""

from typing import Any

from .ast import Node
from .evaluator import Evaluator
from .exceptions import RuleError, RuleEvaluationError, RuleSyntaxError
from .lexer import Lexer
from .parser import Parser

def parse_rule(expression: str) -> Node:
    """Parse a rule expression string into an AST."""
    lexer = Lexer(expression)
    parser = Parser(lexer)
    return parser.parse()

def evaluate_rule(node: Node, context: dict[str, Any]) -> Any:
    """Evaluate a parsed rule AST against a context."""
    evaluator = Evaluator(context)
    return evaluator.evaluate(node)

__all__ = [
    "parse_rule",
    "evaluate_rule",
    "Node",
    "RuleError",
    "RuleSyntaxError",
    "RuleEvaluationError",
]
