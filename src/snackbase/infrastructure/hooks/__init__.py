"""Infrastructure hooks module.

Contains built-in hooks and hook registration utilities.
"""

from snackbase.infrastructure.hooks.builtin_hooks import (
    BUILTIN_HOOKS,
    account_isolation_hook,
    created_by_hook,
    register_builtin_hooks,
    timestamp_hook,
)

__all__ = [
    "BUILTIN_HOOKS",
    "account_isolation_hook",
    "created_by_hook",
    "register_builtin_hooks",
    "timestamp_hook",
]
