"""SQL compiler for rule expressions.

Compiles AST nodes to SQL WHERE clause fragments with parameterized queries.
"""

from typing import Any

from .ast import BinaryOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError


class SQLCompiler:
    """Compiles rule expression AST to SQL WHERE clauses."""

    # Valid context variables
    VALID_AUTH_VARS = {"id", "email", "role", "account_id"}
    VALID_DATA_PREFIX = "@request.data."
    VALID_AUTH_PREFIX = "@request.auth."

    def __init__(self):
        self.param_counter = 0
        self.params: dict[str, Any] = {}

    def compile(
        self, node: Node, auth_context: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        """Compile AST node to SQL WHERE clause.

        Args:
            node: AST node to compile
            auth_context: Authentication context with user info

        Returns:
            Tuple of (SQL fragment, parameter bindings)

        Raises:
            RuleEvaluationError: If compilation fails
        """
        self.param_counter = 0
        self.params = {}
        auth_context = auth_context or {}

        sql = self._compile_node(node, auth_context)
        return sql, self.params

    def _compile_node(self, node: Node, auth_context: dict[str, Any]) -> str:
        """Recursively compile AST node to SQL."""
        if isinstance(node, Literal):
            return self._compile_literal(node)

        if isinstance(node, Variable):
            return self._compile_variable(node, auth_context)

        if isinstance(node, BinaryOp):
            return self._compile_binary_op(node, auth_context)

        if isinstance(node, UnaryOp):
            return self._compile_unary_op(node, auth_context)

        raise RuleEvaluationError(f"Unknown node type: {type(node)}")

    def _compile_literal(self, node: Literal) -> str:
        """Compile literal value to parameterized SQL."""
        param_name = f"param_{self.param_counter}"
        self.param_counter += 1
        self.params[param_name] = node.value
        return f":{param_name}"

    def _compile_variable(self, node: Variable, auth_context: dict[str, Any]) -> str:
        """Compile variable to SQL column or parameter.

        Variables can be:
        - @request.auth.* → parameterized from auth context
        - @request.data.* → parameterized from request data
        - field_name → direct column reference
        """
        var_name = node.name

        # Handle @request.auth.* context variables
        if var_name.startswith(self.VALID_AUTH_PREFIX):
            field = var_name[len(self.VALID_AUTH_PREFIX) :]
            if field not in self.VALID_AUTH_VARS:
                raise RuleEvaluationError(
                    f"Invalid context variable: {var_name}. "
                    f"Valid: {', '.join(f'@request.auth.{v}' for v in self.VALID_AUTH_VARS)}"
                )

            # Create parameter from auth context
            param_name = f"auth_{field}"
            self.params[param_name] = auth_context.get(field, "")
            return f":{param_name}"

        # Handle @request.data.* context variables
        if var_name.startswith(self.VALID_DATA_PREFIX):
            field = var_name[len(self.VALID_DATA_PREFIX) :]
            # For @request.data.*, we'll create a parameter placeholder
            # The actual value will be bound at runtime during create/update
            param_name = f"data_{field}"
            self.params[param_name] = None  # Placeholder
            return f":{param_name}"

        # Regular field name - direct column reference
        # Validate it's a valid identifier (alphanumeric + underscore)
        if not var_name.replace("_", "").isalnum():
            raise RuleEvaluationError(f"Invalid field name: {var_name}")

        return var_name

    def _compile_binary_op(self, node: BinaryOp, auth_context: dict[str, Any]) -> str:
        """Compile binary operation to SQL."""
        left = self._compile_node(node.left, auth_context)
        right = self._compile_node(node.right, auth_context)

        # Map operators to SQL
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

        # For logical operators, wrap in parentheses
        if sql_op in ("AND", "OR"):
            return f"({left} {sql_op} {right})"

        return f"{left} {sql_op} {right}"

    def _compile_unary_op(self, node: UnaryOp, auth_context: dict[str, Any]) -> str:
        """Compile unary operation to SQL."""
        operand = self._compile_node(node.operand, auth_context)

        if node.operator == "!":
            return f"NOT ({operand})"

        raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")


def compile_to_sql(
    expression: str, auth_context: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    """Compile a rule expression to SQL WHERE clause.

    Args:
        expression: Rule expression string
        auth_context: Authentication context with user info

    Returns:
        Tuple of (SQL fragment, parameter bindings)

    Special cases:
        - Empty string "" → ("1=1", {}) (public access)
        - None → ("1=0", {}) (locked/deny all)

    Examples:
        >>> compile_to_sql("created_by = @request.auth.id", {"id": "user123"})
        ("created_by = :auth_id", {"auth_id": "user123"})

        >>> compile_to_sql("status = 'published' && public = true")
        ("(status = :param_0 AND public = :param_1)", {"param_0": "published", "param_1": True})

        >>> compile_to_sql("")
        ("1=1", {})
    """
    # Handle special cases
    if expression is None:
        return ("1=0", {})  # Locked - deny all

    if expression == "":
        return ("1=1", {})  # Public - allow all

    # Parse and compile
    from .lexer import Lexer
    from .parser import Parser

    lexer = Lexer(expression)
    parser = Parser(lexer)
    ast = parser.parse()

    compiler = SQLCompiler()
    return compiler.compile(ast, auth_context)
