"""Rule Expression Parser API."""

from typing import Any

from .ast import Node
from .evaluator import Evaluator
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


async def evaluate_rule(
    node: Node, context: dict[str, Any], macro_engine: Any | None = None
) -> Any:
    """Evaluate a parsed rule AST against a context."""
    evaluator = Evaluator(context, macro_engine)
    return await evaluator.evaluate(node)


__all__ = [
    "parse_rule",
    "evaluate_rule",
    "compile_to_sql",
    "validate_rule_expression",
    "Node",
    "RuleError",
    "RuleSyntaxError",
    "RuleEvaluationError",
]

