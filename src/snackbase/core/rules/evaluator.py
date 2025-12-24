"""Evaluator for rule expressions."""

from typing import Any

from datetime import datetime

from .ast import BinaryOp, FunctionCall, Literal, Node, UnaryOp, Variable
from .exceptions import RuleEvaluationError

class Evaluator:
    """Evaluates an AST against a context."""

    def __init__(self, context: dict[str, Any]):
        self.context = context

    def evaluate(self, node: Node) -> Any:
        """Evaluate a node."""
        if isinstance(node, Literal):
            return node.value
        
        if isinstance(node, Variable):
            return self._resolve_variable(node.name)
        
        if isinstance(node, BinaryOp):
            return self._evaluate_binary(node)
        
        if isinstance(node, UnaryOp):
            return self._evaluate_unary(node)
        
        if isinstance(node, FunctionCall):
            return self._evaluate_function(node)
        
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

    def _evaluate_binary(self, node: BinaryOp) -> Any: # noqa: C901
        """Evaluate binary operations."""
        # Short-circuit logic for AND/OR
        if node.operator == "and":
            left = self.evaluate(node.left)
            if not bool(left):
                return False
            return bool(self.evaluate(node.right))
            
        if node.operator == "or":
            left = self.evaluate(node.left)
            if bool(left):
                return True
            return bool(self.evaluate(node.right))
            
        # Standard evaluation for others
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
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
            
        raise RuleEvaluationError(f"Unknown binary operator: {op}")

    def _evaluate_unary(self, node: UnaryOp) -> Any:
        """Evaluate unary operations."""
        if node.operator == "not":
            # For NOT, we need to evaluate the operand first
            operand = self.evaluate(node.operand)
            return not bool(operand)
            
        raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")

    def _evaluate_function(self, node: FunctionCall) -> Any:
        """Evaluate function calls."""
        args = [self.evaluate(arg) for arg in node.arguments]
        
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
            
        # --- Built-in Macros ---
        
        if node.name == "@has_group":
            if len(args) != 1:
                raise RuleEvaluationError("@has_group() expects 1 argument")
            group_name = args[0]
            user = self.context.get("user")
            if not user or not hasattr(user, "groups") and not isinstance(user, dict):
                 return False
            
            groups = user.get("groups") if isinstance(user, dict) else getattr(user, "groups", [])
            if not groups:
                return False
                
            return group_name in groups

        if node.name == "@has_role":
            if len(args) != 1:
                raise RuleEvaluationError("@has_role() expects 1 argument")
            role_name = args[0]
            user = self.context.get("user")
            if not user:
                return False
                
            role = user.get("role") if isinstance(user, dict) else getattr(user, "role", None)
            return role == role_name

        if node.name in ("@owns_record", "@is_creator"):
            if len(args) != 0:
                raise RuleEvaluationError(f"{node.name}() expects 0 arguments")
            
            user = self.context.get("user")
            record = self.context.get("record")
            
            if not user or not record:
                return False
                
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            
            # Record owner_id could be direct attribute or dict key
            owner_id = None
            if isinstance(record, dict):
                owner_id = record.get("owner_id")
            else:
                owner_id = getattr(record, "owner_id", None)
                
            if user_id is None or owner_id is None:
                return False
                
            return user_id == owner_id

        if node.name == "@in_time_range":
            if len(args) != 2:
                raise RuleEvaluationError("@in_time_range() expects 2 arguments (start_hour, end_hour)")
            
            start_hour = args[0]
            end_hour = args[1]
            
            if not isinstance(start_hour, (int, float)) or not isinstance(end_hour, (int, float)):
                 raise RuleEvaluationError("Time range arguments must be numbers (0-23)")

            current_hour = datetime.now().hour
            return start_hour <= current_hour < end_hour

        if node.name == "@has_permission":
            # This is a bit recursive/meta: checking if user has a permission
            # Usually implies checking role permissions or direct assignments
            # For now, we can check basic role permissions map if present in context
            if len(args) != 2:
                 raise RuleEvaluationError("@has_permission() expects 2 arguments (action, collection)")
                 
            action = args[0]
            collection = args[1]
            
            # Simple implementation: check if "permissions" dict exists in context
            # and follows structure permissions[collection][action]
            permissions = self.context.get("permissions")
            if not permissions or not isinstance(permissions, dict):
                return False
                
            collection_perms = permissions.get(collection)
            if not collection_perms or not isinstance(collection_perms, list):
                return False
                
            return action in collection_perms

        raise RuleEvaluationError(f"Unknown function: {node.name}")
