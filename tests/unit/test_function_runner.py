"""Unit/integration-ish tests for FunctionRunner with real subprocess + venv."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from snackbase.infrastructure.functions.env_builder import build_function_env, compute_version_sha
from snackbase.infrastructure.functions.runner import FunctionRunner

HELLO_HANDLER = '''
from snackbase_fn import Request, Response

def handler(req: Request) -> Response:
    return Response.json({"hello": "world", "method": req.method})
'''

ASYNC_HANDLER = '''
from snackbase_fn import Request, Response

async def handler(req: Request) -> Response:
    return Response.json({"async": True})
'''

CRASH_HANDLER = '''
def handler(req):
    raise RuntimeError("boom")
'''

TIMEOUT_HANDLER = '''
import time

def handler(req):
    time.sleep(60)
    return {"never": True}
'''

SECRET_PROBE_HANDLER = '''
import os
from snackbase_fn import Response

def handler(req):
    return Response.json({
        "has_encryption_key": "SNACKBASE_ENCRYPTION_KEY" in os.environ,
        "fn_slug": os.environ.get("FN_SLUG"),
        "my_secret": os.environ.get("MY_SECRET"),
    })
'''


@pytest.fixture(scope="module")
def function_env(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("fn_envs")
    sha = compute_version_sha({"handler.py": HELLO_HANDLER}, [])
    return build_function_env(
        base_path=base,
        account_id="acc",
        function_id="fn",
        version_sha=sha,
        dependencies=[],
        python_executable=sys.executable,
    )


def test_hello_handler(function_env: Path) -> None:
    runner = FunctionRunner(timeout_seconds=15)
    result = runner.invoke(
        env_path=function_env,
        source_files={"handler.py": HELLO_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "POST", "path": "/", "headers": {}, "json": {}},
        extra_env={"FN_SLUG": "hello"},
    )
    assert result.status == "success", (result.error_message, result.stderr, result.stdout)
    assert result.http_status == 200
    assert result.body == {"hello": "world", "method": "POST"}


def test_async_handler(function_env: Path) -> None:
    runner = FunctionRunner(timeout_seconds=15)
    result = runner.invoke(
        env_path=function_env,
        source_files={"handler.py": ASYNC_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "GET", "path": "/", "headers": {}},
    )
    assert result.status == "success", result.error_message
    assert result.body == {"async": True}


def test_crash_handler(function_env: Path) -> None:
    runner = FunctionRunner(timeout_seconds=15)
    result = runner.invoke(
        env_path=function_env,
        source_files={"handler.py": CRASH_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "GET", "path": "/"},
    )
    assert result.status == "failed"
    assert result.http_status == 500
    assert result.error_message and "boom" in result.error_message


def test_timeout_handler(function_env: Path) -> None:
    runner = FunctionRunner(timeout_seconds=1)
    result = runner.invoke(
        env_path=function_env,
        source_files={"handler.py": TIMEOUT_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "GET", "path": "/"},
    )
    assert result.status == "timeout"
    assert result.http_status == 504


def test_host_encryption_key_not_injected(function_env: Path) -> None:
    runner = FunctionRunner(timeout_seconds=15)
    result = runner.invoke(
        env_path=function_env,
        source_files={"handler.py": SECRET_PROBE_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "GET", "path": "/"},
        extra_env={
            "SNACKBASE_ENCRYPTION_KEY": "should-not-appear",
            "FN_SLUG": "probe",
            "MY_SECRET": "injected",
        },
    )
    assert result.status == "success", result.error_message
    assert result.body["has_encryption_key"] is False
    assert result.body["fn_slug"] == "probe"
    assert result.body["my_secret"] == "injected"


def test_relative_env_path_works(function_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Relative env paths (as stored with default function_env_base_path) must
    still work when the runner chdirs into a temp workdir for subprocess exec.
    """
    # Simulate DB-stored relative path by chdir'ing to the env's parent chain
    # and invoking with a relative path string.
    abs_env = function_env.resolve()
    # Walk up so relative path "fn/<sha>" is valid from a temporary parent
    parent = abs_env.parent.parent  # .../acc
    rel = abs_env.relative_to(parent)
    monkeypatch.chdir(parent)

    runner = FunctionRunner(timeout_seconds=15)
    result = runner.invoke(
        env_path=str(rel),
        source_files={"handler.py": HELLO_HANDLER},
        entrypoint="handler.py",
        request_payload={"method": "POST", "path": "/", "headers": {}, "json": {}},
    )
    assert result.status == "success", (result.error_message, result.stderr, result.stdout)
    assert result.body == {"hello": "world", "method": "POST"}
