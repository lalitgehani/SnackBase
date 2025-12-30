"""Global context management using ContextVars.

This module provides a thread-safe way to store and retrieve the current
HookContext during a request lifecycle, accessible from anywhere in the
application (like deep inside DB repositories or event listeners) without
explicit parameter passing.
"""

from contextvars import ContextVar
from typing import Optional

from snackbase.domain.entities.hook_context import HookContext

# Global context variable for HookContext
_current_hook_context: ContextVar[Optional[HookContext]] = ContextVar(
    "current_hook_context", default=None
)


def get_current_context() -> Optional[HookContext]:
    """Get the current hook context.

    Returns:
        The current HookContext or None if not set.
    """
    return _current_hook_context.get()


def set_current_context(context: HookContext) -> None:
    """Set the current hook context.

    Args:
        context: The HookContext to set.
    """
    _current_hook_context.set(context)


def clear_current_context() -> None:
    """Clear the current hook context."""
    _current_hook_context.set(None)
