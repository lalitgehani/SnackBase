"""In-process concurrency semaphores for function invokes."""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict


class FunctionConcurrencyLimiter:
    """Track concurrent invokes per account and globally."""

    def __init__(
        self,
        *,
        per_account: int = 5,
        global_limit: int = 32,
    ) -> None:
        self._per_account = max(1, per_account)
        self._global_limit = max(1, global_limit)
        self._lock = threading.Lock()
        self._global_count = 0
        self._account_counts: dict[str, int] = defaultdict(int)
        self._async_lock = asyncio.Lock()

    def try_acquire(self, account_id: str) -> bool:
        with self._lock:
            if self._global_count >= self._global_limit:
                return False
            if self._account_counts[account_id] >= self._per_account:
                return False
            self._global_count += 1
            self._account_counts[account_id] += 1
            return True

    def release(self, account_id: str) -> None:
        with self._lock:
            self._global_count = max(0, self._global_count - 1)
            current = self._account_counts.get(account_id, 0)
            if current <= 1:
                self._account_counts.pop(account_id, None)
            else:
                self._account_counts[account_id] = current - 1

    def reconfigure(self, *, per_account: int | None = None, global_limit: int | None = None) -> None:
        with self._lock:
            if per_account is not None:
                self._per_account = max(1, per_account)
            if global_limit is not None:
                self._global_limit = max(1, global_limit)


# Process-wide limiter (configured on first use from settings)
_limiter: FunctionConcurrencyLimiter | None = None
_limiter_lock = threading.Lock()


def get_function_concurrency_limiter() -> FunctionConcurrencyLimiter:
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                try:
                    from snackbase.core.config import get_settings

                    settings = get_settings()
                    _limiter = FunctionConcurrencyLimiter(
                        per_account=settings.max_concurrent_function_invokes_per_account,
                        global_limit=settings.max_concurrent_function_invokes_global,
                    )
                except Exception:
                    _limiter = FunctionConcurrencyLimiter()
    return _limiter


def reset_function_concurrency_limiter() -> None:
    """Test helper to clear the process-wide limiter."""
    global _limiter
    with _limiter_lock:
        _limiter = None
