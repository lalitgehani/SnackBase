"""Rule expression validator.

Validates rule expressions before saving to database.
"""

from .ast import BinaryOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleSyntaxError
from .lexer import Lexer
from .parser import Parser


class RuleValidator:
    """Validates rule expressions."""

    # Valid context variables
    VALID_AUTH_VARS = {"id", "email", "role", "account_id"}
    VALID_DATA_PREFIX = "@request.data."
    VALID_AUTH_PREFIX = "@request.auth."

    # Operations that allow @request.data.*
    DATA_ALLOWED_OPERATIONS = {"create", "update"}

    def __init__(self, collection_fields: list[str], operation: str):
        """Initialize validator.

        Args:
            collection_fields: List of valid field names in the collection
            operation: Operation type (list, view, create, update, delete)
        """
        self.collection_fields = set(collection_fields)
        self.operation = operation
        self.errors: list[str] = []

    def validate(self, expression: str) -> None:
        """Validate a rule expression.

        Args:
            expression: Rule expression string

        Raises:
            RuleSyntaxError: If expression is invalid
        """
        # Handle special cases
        if expression is None or expression == "":
            return  # null (locked) and "" (public) are always valid

        # Parse expression
        try:
            lexer = Lexer(expression)
            parser = Parser(lexer)
            ast = parser.parse()
        except RuleSyntaxError:
            raise  # Re-raise parsing errors as-is

        # Validate AST
        self.errors = []
        self._validate_node(ast)

        if self.errors:
            raise RuleSyntaxError("; ".join(self.errors))

    def _validate_node(self, node: Node) -> None:
        """Recursively validate AST node."""
        if isinstance(node, Literal):
            # Literals are always valid
            return

        if isinstance(node, Variable):
            self._validate_variable(node)
            return

        if isinstance(node, BinaryOp):
            self._validate_node(node.left)
            self._validate_node(node.right)
            return

        if isinstance(node, UnaryOp):
            self._validate_node(node.operand)
            return

        self.errors.append(f"Unknown node type: {type(node)}")

    def _validate_variable(self, node: Variable) -> None:
        """Validate variable reference."""
        var_name = node.name

        # Check @request.auth.* variables
        if var_name.startswith(self.VALID_AUTH_PREFIX):
            field = var_name[len(self.VALID_AUTH_PREFIX) :]
            if field not in self.VALID_AUTH_VARS:
                valid_vars = ", ".join(
                    f"@request.auth.{v}" for v in sorted(self.VALID_AUTH_VARS)
                )
                self.errors.append(
                    f"Invalid context variable '{var_name}'. Valid: {valid_vars}"
                )
            return

        # Check @request.data.* variables
        if var_name.startswith(self.VALID_DATA_PREFIX):
            if self.operation not in self.DATA_ALLOWED_OPERATIONS:
                self.errors.append(
                    f"'@request.data.*' can only be used in create/update rules, "
                    f"not in '{self.operation}' rules"
                )
            return

        # Regular field name - must exist in collection schema
        if var_name not in self.collection_fields:
            self.errors.append(
                f"Field '{var_name}' does not exist in collection. "
                f"Available fields: {', '.join(sorted(self.collection_fields))}"
            )


def validate_rule_expression(
    expression: str, operation: str, collection_fields: list[str]
) -> None:
    """Validate a rule expression.

    Args:
        expression: Rule expression string
        operation: Operation type (list, view, create, update, delete)
        collection_fields: List of valid field names in the collection

    Raises:
        RuleSyntaxError: If expression is invalid

    Examples:
        >>> validate_rule_expression("created_by = @request.auth.id", "list", ["created_by"])
        # OK

        >>> validate_rule_expression("invalid_field = 'test'", "list", ["created_by"])
        # Raises: RuleSyntaxError: Field 'invalid_field' does not exist in collection

        >>> validate_rule_expression("@request.data.title = 'test'", "list", ["title"])
        # Raises: RuleSyntaxError: '@request.data.*' can only be used in create/update rules
    """
    validator = RuleValidator(collection_fields, operation)
    validator.validate(expression)
