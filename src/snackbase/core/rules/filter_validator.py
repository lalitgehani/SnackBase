"""Filter expression validator.

Validates user-provided filter expressions against collection schema before compilation.
More restrictive than RuleValidator: rejects context variables, validates operator/type
compatibility, and only allows known collection fields and system fields.
"""

from typing import Any

from .ast import BinaryOp, InOp, IsNullOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleSyntaxError
from .lexer import Lexer
from .parser import Parser

# System fields always available for filtering
SYSTEM_FIELDS = {
    "id",
    "account_id",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
}

# System field types for operator validation
SYSTEM_FIELD_TYPES: dict[str, str] = {
    "id": "text",
    "account_id": "text",
    "created_at": "datetime",
    "updated_at": "datetime",
    "created_by": "text",
    "updated_by": "text",
}

# Operators allowed for each field type
# Keys must match the 'type' values in collection schema
_ALL_COMPARISON_OPS = {"=", "!=", ">", "<", ">=", "<=", "~", "IN", "IS NULL", "IS NOT NULL"}
_NO_LIKE = {"=", "!=", ">", "<", ">=", "<=", "IN", "IS NULL", "IS NOT NULL"}
_EQUALITY_ONLY = {"=", "!=", "IN", "IS NULL", "IS NOT NULL"}
_BOOLEAN_OPS = {"=", "!=", "IS NULL", "IS NOT NULL"}
_NULL_ONLY = {"IS NULL", "IS NOT NULL"}

FIELD_TYPE_OPERATORS: dict[str, set[str]] = {
    "text": _ALL_COMPARISON_OPS,
    "email": _ALL_COMPARISON_OPS,
    "url": _ALL_COMPARISON_OPS,
    "number": _NO_LIKE,
    "boolean": _BOOLEAN_OPS,
    "date": _NO_LIKE,
    "datetime": _NO_LIKE,
    "reference": _EQUALITY_ONLY,
    "json": _NULL_ONLY,
    # Fallback for unknown types: allow all
}

# Map AST operator strings to display names for error messages
OPERATOR_DISPLAY: dict[str, str] = {
    "=": "=",
    "!=": "!=",
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "~": "~ (LIKE)",
    "IN": "IN",
    "IS NULL": "IS NULL",
    "IS NOT NULL": "IS NOT NULL",
}


class FilterValidator:
    """Validates filter expressions against collection schema."""

    def __init__(self, schema: list[dict[str, Any]]) -> None:
        """Initialize the validator.

        Args:
            schema: Collection schema — list of field dicts with 'name' and 'type' keys.
        """
        self.schema_fields: dict[str, str] = {
            f["name"]: f.get("type", "text").lower() for f in schema
        }
        self.all_valid_fields = set(self.schema_fields.keys()) | SYSTEM_FIELDS
        self.errors: list[str] = []

    def validate(self, expression: str) -> None:
        """Validate a filter expression.

        Args:
            expression: Filter expression string

        Raises:
            RuleSyntaxError: If expression is invalid (bad field, context var, bad operator)
        """
        if not expression or expression.strip() == "":
            return  # Empty filter is always valid

        try:
            lexer = Lexer(expression)
            parser = Parser(lexer)
            ast = parser.parse()
        except RuleSyntaxError:
            raise  # Re-raise parsing errors as-is

        self.errors = []
        self._validate_node(ast)

        if self.errors:
            raise RuleSyntaxError("; ".join(self.errors))

    def _get_field_type(self, field_name: str) -> str:
        """Get the type for a field name."""
        if field_name in self.schema_fields:
            return self.schema_fields[field_name]
        if field_name in SYSTEM_FIELD_TYPES:
            return SYSTEM_FIELD_TYPES[field_name]
        return "text"  # Fallback

    def _check_operator_for_field(self, field_name: str, operator: str) -> None:
        """Check if an operator is valid for a field's type."""
        field_type = self._get_field_type(field_name)
        allowed_ops = FIELD_TYPE_OPERATORS.get(field_type, _ALL_COMPARISON_OPS)
        if operator not in allowed_ops:
            allowed_display = sorted(allowed_ops)
            self.errors.append(
                f"Operator '{operator}' is not supported for field '{field_name}' "
                f"of type '{field_type}'. "
                f"Allowed operators: {', '.join(allowed_display)}"
            )

    def _validate_node(self, node: Node) -> None:
        """Recursively validate AST node."""
        if isinstance(node, Literal):
            return

        if isinstance(node, Variable):
            self._validate_variable(node)
            return

        if isinstance(node, BinaryOp):
            # For logical operators, just recurse
            if node.operator in ("&&", "||"):
                self._validate_node(node.left)
                self._validate_node(node.right)
                return
            # For comparison operators, validate field + operator compatibility
            if isinstance(node.left, Variable):
                self._validate_variable(node.left)
                self._check_operator_for_field(node.left.name, node.operator)
            else:
                self._validate_node(node.left)
            self._validate_node(node.right)
            return

        if isinstance(node, UnaryOp):
            self._validate_node(node.operand)
            return

        if isinstance(node, InOp):
            if isinstance(node.operand, Variable):
                self._validate_variable(node.operand)
                self._check_operator_for_field(node.operand.name, "IN")
            else:
                self._validate_node(node.operand)
            for v in node.values:
                self._validate_node(v)
            return

        if isinstance(node, IsNullOp):
            operator = "IS NULL" if node.is_null else "IS NOT NULL"
            if isinstance(node.operand, Variable):
                self._validate_variable(node.operand)
                self._check_operator_for_field(node.operand.name, operator)
            else:
                self._validate_node(node.operand)
            return

        self.errors.append(f"Unknown node type: {type(node)}")

    def _validate_variable(self, node: Variable) -> None:
        """Validate a variable reference in a filter expression."""
        var_name = node.name

        # Reject context variables
        if var_name.startswith("@"):
            self.errors.append(
                f"Context variables are not allowed in filters: '{var_name}'. "
                "Use plain field names only (e.g., status, price, created_at)."
            )
            return

        # Field must exist in schema or system fields
        if var_name not in self.all_valid_fields:
            available = sorted(self.all_valid_fields)
            self.errors.append(
                f"Field '{var_name}' does not exist in collection. "
                f"Available fields: {', '.join(available)}"
            )


def validate_filter_expression(
    expression: str,
    schema: list[dict[str, Any]],
) -> None:
    """Validate a filter expression against a collection schema.

    Args:
        expression: Filter expression string
        schema: Collection schema — list of field dicts with 'name' and 'type' keys

    Raises:
        RuleSyntaxError: If expression is invalid

    Examples:
        >>> validate_filter_expression('status = "active"', [{"name": "status", "type": "text"}])
        # OK

        >>> validate_filter_expression('nonexistent = "x"', [{"name": "status", "type": "text"}])
        # Raises: RuleSyntaxError: Field 'nonexistent' does not exist...

        >>> validate_filter_expression('@request.auth.id = "x"', schema)
        # Raises: RuleSyntaxError: Context variables are not allowed in filters...

        >>> validate_filter_expression('is_active > true', [{"name": "is_active", "type": "boolean"}])
        # Raises: RuleSyntaxError: Operator '>' is not supported for field 'is_active'...
    """
    validator = FilterValidator(schema)
    validator.validate(expression)
