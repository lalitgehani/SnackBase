"""Evaluator for rule expressions."""

from typing import Any

from .ast import BinaryOp, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError
from ..macros.engine import MacroExecutionEngine


class Evaluator:
    """Evaluates an AST against a context."""

    def __init__(
        self, context: dict[str, Any], macro_engine: MacroExecutionEngine | None = None
    ):
        """Initialize the evaluator.

        Args:
            context: The data context (user, record, etc.)
            macro_engine: Optional engine for executing macros.
        """
        self.context = context
        self.macro_engine = macro_engine

    async def evaluate(self, node: Node) -> Any:
        """Evaluate a node."""
        if isinstance(node, Literal):
            return node.value

        if isinstance(node, Variable):
            return self._resolve_variable(node.name)

        if isinstance(node, BinaryOp):
            return await self._evaluate_binary(node)

        if isinstance(node, UnaryOp):
            return await self._evaluate_unary(node)

        raise RuleEvaluationError(f"Unknown node type: {type(node).__name__}")

    def _resolve_variable(self, name: str) -> Any:
        """Resolve a variable from the context."""
        parts = name.split(".")
        value = self.context

        for part in parts:
            if value is None:
                return None

            # 1. Try dictionary access
            if isinstance(value, dict):
                if part in value:
                    value = value[part]
                    continue

            # 2. Try object attribute access
            if hasattr(value, part):
                value = getattr(value, part)
                continue

            # 3. Not found
            return None

        return value

    async def _evaluate_binary(self, node: BinaryOp) -> Any:
        """Evaluate binary operations."""
        # Short-circuit logic for AND/OR (support both old and new syntax)
        if node.operator in ("and", "&&"):
            left = await self.evaluate(node.left)
            if not bool(left):
                return False
            return bool(await self.evaluate(node.right))

        if node.operator in ("or", "||"):
            left = await self.evaluate(node.left)
            if bool(left):
                return True
            return bool(await self.evaluate(node.right))

        # Standard evaluation for others
        left = await self.evaluate(node.left)
        right = await self.evaluate(node.right)
        op = node.operator

        # Support both old (==) and new (=) syntax
        if op in ("==", "="):
            return left == right
        if op == "!=":
            return left != right

        # Comparison operators require comparable types
        try:
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
        except TypeError:
            # If types are incompatible (e.g. None < 5), return False
            return False

        # LIKE operator (~) - convert to string contains
        if op == "~":
            if left is None or right is None:
                return False
            try:
                # Simple LIKE implementation: % is wildcard
                pattern = str(right).replace("%", ".*")
                import re

                return bool(re.match(pattern, str(left)))
            except (TypeError, re.error):
                return False

        raise RuleEvaluationError(f"Unknown binary operator: {op}")

    async def _evaluate_unary(self, node: UnaryOp) -> Any:
        """Evaluate unary operations."""
        # Support both old (not) and new (!) syntax
        if node.operator in ("not", "!"):
            # For NOT, we need to evaluate the operand first
            operand = await self.evaluate(node.operand)
            return not bool(operand)

        raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")

