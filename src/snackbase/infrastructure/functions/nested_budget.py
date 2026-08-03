"""Nested function invoke budget tracking."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class NestedInvokeBudget:
    """Track nested invoke counts within a rolling one-minute window."""

    def __init__(self, limit_per_minute: int = 30) -> None:
        self._limit = max(1, limit_per_minute)
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def reconfigure(self, limit_per_minute: int) -> None:
        with self._lock:
            self._limit = max(1, limit_per_minute)

    def check_and_increment(self, root_key: str, depth: int) -> bool:
        """Return True if allowed, False if over budget.

        Depth 0 (root external invoke) always allowed and does not consume budget.
        Nested (depth >= 1) consumes budget.
        """
        if depth <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            q = self._events[root_key]
            while q and now - q[0] > 60.0:
                q.popleft()
            if len(q) >= self._limit:
                return False
            q.append(now)
            return True


_budget: NestedInvokeBudget | None = None
_budget_lock = threading.Lock()


def get_nested_invoke_budget() -> NestedInvokeBudget:
    global _budget
    if _budget is None:
        with _budget_lock:
            if _budget is None:
                try:
                    from snackbase.core.config import get_settings

                    settings = get_settings()
                    _budget = NestedInvokeBudget(
                        settings.function_nested_invoke_limit_per_minute
                    )
                except Exception:
                    _budget = NestedInvokeBudget()
    return _budget


def reset_nested_invoke_budget() -> None:
    global _budget
    with _budget_lock:
        _budget = None
