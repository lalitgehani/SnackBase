"""Evaluator for rule expressions."""

from typing import Any

from .ast import BinaryOp, FunctionCall, ListLiteral, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError
from ..macros.engine import MacroExecutionEngine


class Evaluator:
    """Evaluates an AST against a context."""

    def __init__(self, context: dict[str, Any], macro_engine: MacroExecutionEngine | None = None):
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
        
        if isinstance(node, FunctionCall):
            return await self._evaluate_function(node)
        
        if isinstance(node, ListLiteral):
            return await self._evaluate_list(node)
        
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
        # Short-circuit logic for AND/OR
        if node.operator == "and":
            left = await self.evaluate(node.left)
            if not bool(left):
                return False
            return bool(await self.evaluate(node.right))
            
        if node.operator == "or":
            left = await self.evaluate(node.left)
            if bool(left):
                return True
            return bool(await self.evaluate(node.right))
            
        # Standard evaluation for others
        left = await self.evaluate(node.left)
        right = await self.evaluate(node.right)
        op = node.operator

        if op == "==":
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
        
        # 'in' operator for membership testing
        if op == "in":
            if right is None:
                return False
            try:
                return left in right
            except TypeError:
                # If right is not iterable, return False
                return False
            
        raise RuleEvaluationError(f"Unknown binary operator: {op}")

    async def _evaluate_unary(self, node: UnaryOp) -> Any:
        """Evaluate unary operations."""
        if node.operator == "not":
            # For NOT, we need to evaluate the operand first
            operand = await self.evaluate(node.operand)
            return not bool(operand)
            
        raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")

    async def _evaluate_function(self, node: FunctionCall) -> Any:
        """Evaluate function calls."""
        # Resolve arguments first
        args = []
        for arg in node.arguments:
            args.append(await self.evaluate(arg))
        
        # Check for Macro calls
        if node.name.startswith("@"):
            if not self.macro_engine:
                 # If no engine provided, we default to deny for macros
                 # Or raise error. Let's return False for now.
                 return False
            return await self.macro_engine.execute_macro(node.name, args, self.context)

        # Standard functions
        if node.name == "contains":
            if len(args) != 2:
                raise RuleEvaluationError("contains() expects 2 arguments")
            container = args[0]
            item = args[1]
            if container is None:
                return False
            return item in container

        if node.name == "starts_with":
            if len(args) != 2:
                raise RuleEvaluationError("starts_with() expects 2 arguments")
            s = args[0]
            prefix = args[1]
            if not isinstance(s, str) or not isinstance(prefix, str):
                return False
            return s.startswith(prefix)

        if node.name == "ends_with":
            if len(args) != 2:
                raise RuleEvaluationError("ends_with() expects 2 arguments")
            s = args[0]
            suffix = args[1]
            if not isinstance(s, str) or not isinstance(suffix, str):
                return False
            return s.endswith(suffix)
            
        raise RuleEvaluationError(f"Unknown function: {node.name}")

    async def _evaluate_list(self, node: ListLiteral) -> Any:
        """Evaluate a list literal to a Python list."""
        result = []
        for item in node.items:
            result.append(await self.evaluate(item))
        return result
