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
    """Represents a variable access (e.g., created_by, @request.auth.id)."""

    name: str


@dataclass
class BinaryOp(Node):
    """Represents a binary operation (e.g., a = b, a && b)."""

    left: Node
    operator: str
    right: Node


@dataclass
class UnaryOp(Node):
    """Represents a unary operation (e.g., !a)."""

    operator: str
    operand: Node

