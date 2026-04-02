"""Expression compiler for computed/virtual fields.

Compiles expression AST nodes to SQL expressions for use in SELECT clauses.
Unlike FilterCompiler (which produces WHERE conditions), ExpressionCompiler
produces scalar SQL expressions — values returned alongside stored columns.

This is the third compiler on the shared core/rules/ parser, alongside
FilterCompiler and RuleCompiler (SQLCompiler).

Supported functions:
  String:  concat, upper, lower, trim, substring, length
  Math:    round, abs, ceil, floor  (+ arithmetic operators via BinaryOp)
  Logic:   if, coalesce, nullif
  Date:    now, date_diff, date_add
"""

from typing import Any

from .ast import BinaryOp, FunctionCall, IsNullOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError, RuleSyntaxError


class ExpressionCompilationError(RuleSyntaxError):
    """Raised when a computed field expression cannot be compiled."""


VALID_FUNCTIONS = frozenset({
    "concat", "upper", "lower", "trim", "substring", "length",
    "round", "abs", "ceil", "floor",
    "if", "coalesce", "nullif",
    "now", "date_diff", "date_add",
})

# Arithmetic operators allowed in computed expressions
ARITHMETIC_OPS = frozenset({"+", "-", "*", "/", "%"})

# Comparison and logical ops — valid when used inside if() conditions
COMPARISON_OPS = frozenset({"=", "!=", "<", ">", "<=", ">=", "~", "&&", "||"})


class ExpressionCompiler:
    """Compiles expression AST to SQL scalar expressions for computed fields.

    Dialect-aware: handles differences between SQLite and PostgreSQL for
    functions like concat, ceil, floor, now, date_diff, date_add.

    Args:
        dialect: Database dialect ("sqlite" or "postgresql").
        schema_fields: Set of valid non-computed field names. If provided,
            variable references are validated against this set.
    """

    def __init__(
        self,
        dialect: str = "sqlite",
        schema_fields: set[str] | None = None,
    ) -> None:
        self.dialect = dialect
        self.schema_fields = schema_fields
        self.param_counter = 0
        self.params: dict[str, Any] = {}

    def compile(self, node: Node) -> tuple[str, dict[str, Any]]:
        """Compile AST node to a SQL scalar expression.

        Args:
            node: AST node to compile.

        Returns:
            Tuple of (SQL expression string, parameter bindings).

        Raises:
            ExpressionCompilationError: If the expression is invalid.
        """
        self.param_counter = 0
        self.params = {}
        sql = self._compile_node(node)
        return sql, self.params

    def _next_param(self, value: Any) -> str:
        """Register a literal value as a bound parameter and return its placeholder."""
        name = f"ec_{self.param_counter}"
        self.param_counter += 1
        self.params[name] = value
        return f":{name}"

    def _compile_node(self, node: Node) -> str:
        """Recursively compile an AST node."""
        if isinstance(node, Literal):
            return self._compile_literal(node)
        if isinstance(node, Variable):
            return self._compile_variable(node)
        if isinstance(node, BinaryOp):
            return self._compile_binary_op(node)
        if isinstance(node, UnaryOp):
            return self._compile_unary_op(node)
        if isinstance(node, FunctionCall):
            return self._compile_function(node)
        if isinstance(node, IsNullOp):
            return self._compile_is_null_op(node)
        raise ExpressionCompilationError(f"Unsupported node type in expression: {type(node).__name__}")

    def _compile_literal(self, node: Literal) -> str:
        return self._next_param(node.value)

    def _compile_variable(self, node: Variable) -> str:
        name = node.name
        if name.startswith("@"):
            raise ExpressionCompilationError(
                f"Context variables are not allowed in computed field expressions: '{name}'"
            )
        if not name.replace("_", "").isalnum():
            raise ExpressionCompilationError(f"Invalid field name in expression: '{name}'")
        if self.schema_fields is not None and name not in self.schema_fields:
            raise ExpressionCompilationError(
                f"Unknown field '{name}' in computed expression. "
                "Computed fields cannot reference other computed fields or non-existent fields."
            )
        return f'"{name}"'

    def _compile_binary_op(self, node: BinaryOp) -> str:
        op = node.operator
        if op in ARITHMETIC_OPS:
            left = self._compile_node(node.left)
            right = self._compile_node(node.right)
            return f"({left} {op} {right})"
        if op in COMPARISON_OPS:
            # Allowed inside if() conditions
            left = self._compile_node(node.left)
            right = self._compile_node(node.right)
            sql_op_map = {
                "=": "=", "!=": "!=", "<": "<", ">": ">",
                "<=": "<=", ">=": ">=", "~": "LIKE",
                "&&": "AND", "||": "OR",
            }
            sql_op = sql_op_map[op]
            return f"({left} {sql_op} {right})"
        raise ExpressionCompilationError(f"Unsupported operator in expression: '{op}'")

    def _compile_unary_op(self, node: UnaryOp) -> str:
        if node.operator == "-":
            operand = self._compile_node(node.operand)
            return f"(-{operand})"
        if node.operator == "!":
            operand = self._compile_node(node.operand)
            return f"(NOT {operand})"
        raise ExpressionCompilationError(f"Unsupported unary operator: '{node.operator}'")

    def _compile_is_null_op(self, node: IsNullOp) -> str:
        operand = self._compile_node(node.operand)
        return f"({operand} IS NULL)" if node.is_null else f"({operand} IS NOT NULL)"

    def _compile_function(self, node: FunctionCall) -> str:  # noqa: C901
        name = node.name.lower()
        if name not in VALID_FUNCTIONS:
            raise ExpressionCompilationError(
                f"Unknown function '{node.name}'. "
                f"Supported functions: {', '.join(sorted(VALID_FUNCTIONS))}"
            )

        args = node.args

        # ── String functions ─────────────────────────────────────────────────

        if name == "concat":
            if len(args) < 2:
                raise ExpressionCompilationError("concat() requires at least 2 arguments")
            compiled = [self._compile_node(a) for a in args]
            if self.dialect == "postgresql":
                return f"CONCAT({', '.join(compiled)})"
            # SQLite: use || operator
            return "(" + " || ".join(compiled) + ")"

        if name == "upper":
            self._require_args(name, args, 1, 1)
            return f"UPPER({self._compile_node(args[0])})"

        if name == "lower":
            self._require_args(name, args, 1, 1)
            return f"LOWER({self._compile_node(args[0])})"

        if name == "trim":
            self._require_args(name, args, 1, 1)
            return f"TRIM({self._compile_node(args[0])})"

        if name == "length":
            self._require_args(name, args, 1, 1)
            return f"LENGTH({self._compile_node(args[0])})"

        if name == "substring":
            self._require_args(name, args, 2, 3)
            src = self._compile_node(args[0])
            start = self._compile_node(args[1])
            if len(args) == 3:
                length = self._compile_node(args[2])
                if self.dialect == "postgresql":
                    return f"SUBSTRING({src} FROM {start} FOR {length})"
                return f"SUBSTR({src}, {start}, {length})"
            if self.dialect == "postgresql":
                return f"SUBSTRING({src} FROM {start})"
            return f"SUBSTR({src}, {start})"

        # ── Math functions ───────────────────────────────────────────────────

        if name == "abs":
            self._require_args(name, args, 1, 1)
            return f"ABS({self._compile_node(args[0])})"

        if name == "round":
            self._require_args(name, args, 1, 2)
            val = self._compile_node(args[0])
            if len(args) == 2:
                decimals = self._compile_node(args[1])
                return f"ROUND({val}, {decimals})"
            return f"ROUND({val})"

        if name == "ceil":
            self._require_args(name, args, 1, 1)
            val = self._compile_node(args[0])
            if self.dialect == "postgresql":
                return f"CEIL({val})"
            # SQLite approximation: smallest integer >= val
            return f"CAST(ROUND({val} + 0.4999999999) AS INTEGER)"

        if name == "floor":
            self._require_args(name, args, 1, 1)
            val = self._compile_node(args[0])
            if self.dialect == "postgresql":
                return f"FLOOR({val})"
            # SQLite: largest integer <= val
            return f"CAST(ROUND({val} - 0.4999999999) AS INTEGER)"

        # ── Logic functions ──────────────────────────────────────────────────

        if name == "if":
            self._require_args(name, args, 3, 3)
            condition = self._compile_node(args[0])
            then_val = self._compile_node(args[1])
            else_val = self._compile_node(args[2])
            return f"CASE WHEN {condition} THEN {then_val} ELSE {else_val} END"

        if name == "coalesce":
            if len(args) < 2:
                raise ExpressionCompilationError("coalesce() requires at least 2 arguments")
            compiled = [self._compile_node(a) for a in args]
            return f"COALESCE({', '.join(compiled)})"

        if name == "nullif":
            self._require_args(name, args, 2, 2)
            a = self._compile_node(args[0])
            b = self._compile_node(args[1])
            return f"NULLIF({a}, {b})"

        # ── Date functions ───────────────────────────────────────────────────

        if name == "now":
            self._require_args(name, args, 0, 0)
            if self.dialect == "postgresql":
                return "NOW()"
            return "datetime('now')"

        if name == "date_diff":
            self._require_args(name, args, 3, 3)
            a = self._compile_node(args[0])
            b = self._compile_node(args[1])
            # unit must be a string literal
            if not isinstance(args[2], Literal) or not isinstance(args[2].value, str):
                raise ExpressionCompilationError(
                    "date_diff() third argument (unit) must be a string literal: "
                    "'days', 'hours', 'minutes', 'seconds', 'months', 'years'"
                )
            unit = args[2].value.lower()
            valid_units = {"days", "hours", "minutes", "seconds", "months", "years"}
            if unit not in valid_units:
                raise ExpressionCompilationError(
                    f"date_diff() unit '{unit}' is not supported. "
                    f"Valid units: {', '.join(sorted(valid_units))}"
                )
            if self.dialect == "postgresql":
                pg_unit_map = {
                    "days": "day", "hours": "hour", "minutes": "minute",
                    "seconds": "second", "months": "month", "years": "year",
                }
                pg_unit = pg_unit_map[unit]
                return f"EXTRACT(EPOCH FROM ({a} - {b})) / {self._epoch_divisor(pg_unit)}"
            # SQLite: use JULIANDAY for days; scale for other units
            sqlite_factor = {
                "days": 1, "hours": 24, "minutes": 1440,
                "seconds": 86400, "months": 30, "years": 365,
            }
            factor = sqlite_factor[unit]
            if factor == 1:
                return f"(JULIANDAY({a}) - JULIANDAY({b}))"
            return f"((JULIANDAY({a}) - JULIANDAY({b})) * {factor})"

        if name == "date_add":
            self._require_args(name, args, 3, 3)
            date_val = self._compile_node(args[0])
            amount = self._compile_node(args[1])
            if not isinstance(args[2], Literal) or not isinstance(args[2].value, str):
                raise ExpressionCompilationError(
                    "date_add() third argument (unit) must be a string literal"
                )
            unit = args[2].value.lower()
            valid_units = {"days", "hours", "minutes", "seconds", "months", "years"}
            if unit not in valid_units:
                raise ExpressionCompilationError(
                    f"date_add() unit '{unit}' is not supported. "
                    f"Valid units: {', '.join(sorted(valid_units))}"
                )
            if self.dialect == "postgresql":
                # e.g. date_val + (amount || ' days')::interval
                unit_singular = unit.rstrip("s")  # 'days' → 'day', 'months' → 'month'
                return f"({date_val} + ({amount} || ' {unit_singular}')::interval)"
            # SQLite: datetime(date_val, amount || ' unit')
            return f"datetime({date_val}, ({amount}) || ' {unit}')"

        # Should never reach here due to VALID_FUNCTIONS check above
        raise ExpressionCompilationError(f"Unhandled function: '{name}'")  # pragma: no cover

    @staticmethod
    def _epoch_divisor(pg_unit: str) -> int:
        """Return seconds-per-unit for PostgreSQL EXTRACT(EPOCH ...) scaling."""
        divisors = {
            "day": 86400, "hour": 3600, "minute": 60, "second": 1,
            "month": 2592000, "year": 31536000,
        }
        return divisors.get(pg_unit, 1)

    @staticmethod
    def _require_args(func_name: str, args: list, min_: int, max_: int) -> None:
        n = len(args)
        if min_ == max_:
            if n != min_:
                raise ExpressionCompilationError(
                    f"{func_name}() requires exactly {min_} argument(s), got {n}"
                )
        elif n < min_ or n > max_:
            raise ExpressionCompilationError(
                f"{func_name}() requires {min_}–{max_} arguments, got {n}"
            )


def compile_expression_to_sql(
    expression: str,
    dialect: str = "sqlite",
    schema_fields: set[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Compile a computed field expression string to a SQL scalar expression.

    Args:
        expression: Expression string (e.g., "price * quantity",
                    "concat(first_name, ' ', last_name)").
        dialect: Database dialect ("sqlite" or "postgresql").
        schema_fields: Set of valid non-computed field names for validation.
            If None, field references are not validated.

    Returns:
        Tuple of (SQL expression string, parameter bindings with 'ec_' prefix).

    Raises:
        ExpressionCompilationError: If the expression is invalid.
        RuleSyntaxError: If the expression has invalid syntax.

    Examples:
        >>> compile_expression_to_sql("price * quantity")
        ('("price" * "quantity")', {})

        >>> compile_expression_to_sql("concat(first_name, ' ', last_name)")
        # SQLite:     ('("first_name" || :ec_0 || "last_name")', {'ec_0': ' '})
        # PostgreSQL: ('CONCAT("first_name", :ec_0, "last_name")', {'ec_0': ' '})
    """
    from .lexer import Lexer
    from .parser import Parser

    if not expression or not expression.strip():
        raise ExpressionCompilationError("Expression cannot be empty")

    lexer = Lexer(expression.strip())
    parser = Parser(lexer)
    ast = parser.parse()

    compiler = ExpressionCompiler(dialect=dialect, schema_fields=schema_fields)
    return compiler.compile(ast)
