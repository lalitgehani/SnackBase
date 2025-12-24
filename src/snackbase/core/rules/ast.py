"""Abstract Syntax Tree nodes for rule expressions."""

from dataclasses import dataclass
from typing import Any

@dataclass
class Node:
    """Base class for all AST nodes."""
    pass

@dataclass
class Literal(Node):
    """Represents a literal value (string, number, boolean, null)."""
    value: Any

@dataclass
class Variable(Node):
    """Represents a variable access (e.g., user.id)."""
    name: str

@dataclass
class BinaryOp(Node):
    """Represents a binary operation (e.g., a == b)."""
    left: Node
    operator: str
    right: Node

@dataclass
class UnaryOp(Node):
    """Represents a unary operation (e.g., not a)."""
    operator: str
    operand: Node

@dataclass
class FunctionCall(Node):
    """Represents a function call (e.g., contains(a, b))."""
    name: str
    arguments: list[Node]
