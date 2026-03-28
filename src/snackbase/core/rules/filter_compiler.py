"""Filter compiler for user-facing filter expressions.

Compiles AST nodes to SQL WHERE clause fragments with parameterized queries.
Unlike SQLCompiler (RuleCompiler), this compiler:
- Only allows plain field names (no @request.auth.*, @request.data.*)
- Uses 'fp_' parameter prefix to avoid collision with rule filter params
- Quotes column names with double-quotes for safety
"""

from typing import Any

from .ast import BinaryOp, InOp, IsNullOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError, RuleSyntaxError


class FilterCompilationError(RuleSyntaxError):
    """Raised when a filter expression cannot be compiled."""


class FilterCompiler:
    """Compiles filter expression AST to SQL WHERE clauses.

    Designed for user-provided filters on the records list endpoint.
    Context variables (@request.auth.*, @request.data.*) are rejected.
    """

    def __init__(self) -> None:
        self.param_counter = 0
        self.params: dict[str, Any] = {}

    def compile(self, node: Node) -> tuple[str, dict[str, Any]]:
        """Compile AST node to SQL WHERE clause.

        Args:
            node: AST node to compile

        Returns:
            Tuple of (SQL fragment, parameter bindings)

        Raises:
            FilterCompilationError: If compilation fails (e.g., context variable used)
        """
        self.param_counter = 0
        self.params = {}
        sql = self._compile_node(node)
        return sql, self.params

    def _compile_node(self, node: Node) -> str:
        """Recursively compile AST node to SQL."""
        if isinstance(node, Literal):
            return self._compile_literal(node)

        if isinstance(node, Variable):
            return self._compile_variable(node)

        if isinstance(node, BinaryOp):
            return self._compile_binary_op(node)

        if isinstance(node, UnaryOp):
            return self._compile_unary_op(node)

        if isinstance(node, InOp):
            return self._compile_in_op(node)

        if isinstance(node, IsNullOp):
            return self._compile_is_null_op(node)

        raise RuleEvaluationError(f"Unknown node type: {type(node)}")

    def _compile_literal(self, node: Literal) -> str:
        """Compile literal value to parameterized SQL."""
        param_name = f"fp_{self.param_counter}"
        self.param_counter += 1
        self.params[param_name] = node.value
        return f":{param_name}"

    def _compile_variable(self, node: Variable) -> str:
        """Compile variable to SQL column reference.

        Only plain field names are allowed. Context variables (@request.*) are rejected.
        """
        var_name = node.name

        # Reject context variables
        if var_name.startswith("@"):
            raise FilterCompilationError(
                f"Context variables are not allowed in filters: '{var_name}'. "
                "Use plain field names only (e.g., status, price, created_at)."
            )

        # Validate it's a safe identifier (alphanumeric + underscore)
        if not var_name.replace("_", "").isalnum():
            raise FilterCompilationError(f"Invalid field name: '{var_name}'")

        # Quote the column name to prevent SQL injection via field name
        return f'"{var_name}"'

    def _compile_binary_op(self, node: BinaryOp) -> str:
        """Compile binary operation to SQL."""
        left = self._compile_node(node.left)
        right = self._compile_node(node.right)

        operator_map = {
            "=": "=",
            "!=": "!=",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
            "~": "LIKE",
            "&&": "AND",
            "||": "OR",
        }

        sql_op = operator_map.get(node.operator)
        if not sql_op:
            raise RuleEvaluationError(f"Unknown operator: {node.operator}")

        if sql_op in ("AND", "OR"):
            return f"({left} {sql_op} {right})"

        return f"{left} {sql_op} {right}"

    def _compile_unary_op(self, node: UnaryOp) -> str:
        """Compile unary operation to SQL."""
        operand = self._compile_node(node.operand)
        if node.operator == "!":
            return f"NOT ({operand})"
        raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")

    def _compile_in_op(self, node: InOp) -> str:
        """Compile IN operation to SQL."""
        left = self._compile_node(node.operand)
        placeholders = []
        for value_node in node.values:
            param_name = f"fp_{self.param_counter}"
            self.param_counter += 1
            self.params[param_name] = value_node.value  # type: ignore[attr-defined]
            placeholders.append(f":{param_name}")
        return f"{left} IN ({', '.join(placeholders)})"

    def _compile_is_null_op(self, node: IsNullOp) -> str:
        """Compile IS NULL / IS NOT NULL to SQL."""
        operand = self._compile_node(node.operand)
        if node.is_null:
            return f"{operand} IS NULL"
        return f"{operand} IS NOT NULL"


def compile_filter_to_sql(expression: str) -> tuple[str, dict[str, Any]]:
    """Compile a user filter expression to SQL WHERE clause.

    Args:
        expression: Filter expression string (e.g., 'status = "active" && price > 100')

    Returns:
        Tuple of (SQL fragment, parameter bindings)

    Special cases:
        - Empty string "" → ("1=1", {}) (no filter)

    Raises:
        FilterCompilationError: If expression contains context variables or invalid identifiers
        RuleSyntaxError: If expression has invalid syntax

    Examples:
        >>> compile_filter_to_sql('status = "active"')
        ('"status" = :fp_0', {"fp_0": "active"})

        >>> compile_filter_to_sql('price > 100')
        ('"price" > :fp_0', {"fp_0": 100})

        >>> compile_filter_to_sql('status IN ("active", "pending")')
        ('"status" IN (:fp_0, :fp_1)', {"fp_0": "active", "fp_1": "pending"})

        >>> compile_filter_to_sql('deleted_at IS NULL')
        ('"deleted_at" IS NULL', {})
    """
    if not expression or expression.strip() == "":
        return ("1=1", {})

    from .lexer import Lexer
    from .parser import Parser

    lexer = Lexer(expression)
    parser = Parser(lexer)
    ast = parser.parse()

    compiler = FilterCompiler()
    return compiler.compile(ast)
