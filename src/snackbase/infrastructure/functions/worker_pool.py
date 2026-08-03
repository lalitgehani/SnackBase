"""Dedicated function worker pool isolating CPU from the API event loop."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from typing import Any

from snackbase.core.logging import get_logger
from snackbase.infrastructure.functions.runner import FunctionRunner, InvokeResult

logger = get_logger(__name__)


class FunctionWorkerPool:
    """Thread-pool backed executor for function subprocess invokes.

    ``submit`` (async) offloads ``runner.invoke`` to the pool so the API
    event loop is never blocked on ``future.result()``.
    """

    def __init__(self, size: int = 4) -> None:
        self._size = max(1, size)
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._size,
            thread_name_prefix="fn-worker",
        )
        self._lock = threading.Lock()
        self._inflight = 0

    @property
    def size(self) -> int:
        return self._size

    @property
    def inflight(self) -> int:
        with self._lock:
            return self._inflight

    def _try_acquire(self) -> bool:
        with self._lock:
            if self._inflight >= self._size * 4:
                return False
            self._inflight += 1
            return True

    def _release(self) -> None:
        with self._lock:
            self._inflight = max(0, self._inflight - 1)

    def _run_invoke(self, runner: FunctionRunner, kwargs: dict[str, Any]) -> InvokeResult:
        """Run invoke on a worker thread (or caller thread for submit_sync)."""
        if not self._try_acquire():
            return InvokeResult(
                status="failed",
                http_status=429,
                error_message="Function worker pool saturated",
            )
        try:
            return runner.invoke(**kwargs)
        finally:
            self._release()

    def submit_sync(self, runner: FunctionRunner, **kwargs: Any) -> InvokeResult:
        """Synchronous invoke for non-async callers (CLI / tests).

        Runs on the current thread; does not block a shared event loop.
        """
        return self._run_invoke(runner, kwargs)

    async def submit(self, runner: FunctionRunner, **kwargs: Any) -> InvokeResult:
        """Offload invoke to the worker pool without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._run_invoke,
            runner,
            kwargs,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


_pool: FunctionWorkerPool | None = None
_pool_lock = threading.Lock()


def get_function_worker_pool() -> FunctionWorkerPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                try:
                    from snackbase.core.config import get_settings

                    size = get_settings().function_worker_pool_size
                except Exception:
                    size = 4
                _pool = FunctionWorkerPool(size=size)
    return _pool


def reset_function_worker_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown()
        _pool = None
