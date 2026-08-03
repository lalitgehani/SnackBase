"""Unit tests for function worker pool and retention helpers."""

from snackbase.infrastructure.functions.runner import FunctionRunner
from snackbase.infrastructure.functions.worker_pool import FunctionWorkerPool


def test_worker_pool_size() -> None:
    pool = FunctionWorkerPool(size=2)
    assert pool.size == 2
    pool.shutdown()


def test_worker_pool_submit_missing_env() -> None:
    pool = FunctionWorkerPool(size=1)
    runner = FunctionRunner(timeout_seconds=5)
    result = pool.submit_sync(
        runner,
        env_path="/nonexistent/env",
        source_files={"handler.py": "def handler(req): return {}"},
        entrypoint="handler.py",
        request_payload={"method": "GET", "path": "/"},
    )
    assert result.status == "failed"
    pool.shutdown()
