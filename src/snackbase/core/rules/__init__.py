"""Rule Expression Parser API."""

from .aggregation_parser import AggFunction, AggregationParseError, parse_agg_functions, parse_having, validate_group_by
from .ast import InOp, IsNullOp, Node
from .exceptions import RuleError, RuleEvaluationError, RuleSyntaxError
from .filter_compiler import FilterCompilationError, compile_filter_to_sql
from .filter_validator import validate_filter_expression
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
    "compile_filter_to_sql",
    "validate_rule_expression",
    "validate_filter_expression",
    "AggFunction",
    "AggregationParseError",
    "parse_agg_functions",
    "parse_having",
    "validate_group_by",
    "Node",
    "InOp",
    "IsNullOp",
    "RuleError",
    "RuleSyntaxError",
    "RuleEvaluationError",
    "FilterCompilationError",
]
