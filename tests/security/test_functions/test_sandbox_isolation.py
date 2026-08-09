"""FN-SBX-*: functions sandbox isolation checks (C-04).

A tenant handler is arbitrary Python, so the boundaries it must not cross are
enforced by the kernel rather than in-process:

* **Filesystem** — the child is Landlock-restricted to its own function env
  and work directory, so the host database file and other tenants' envs are
  not reachable.
* **Egress** — the policy is applied at ``socket.connect``, not only to
  ``httpx``/``urllib``, so a handler opening a raw socket is still classified.
* **Resources** — ``setrlimit`` bounds address space and CPU time, so a runaway
  allocation is stopped by the kernel and not only by the wall clock.

The environment allowlist is locked in as a plain regression (FN-SBX-020).

Two of these depend on the platform, and are skipped rather than silently
passing where the mechanism does not exist:

* filesystem confinement needs Landlock, so it holds on Linux 5.13+ only;
* macOS refuses ``setrlimit(RLIMIT_AS)`` outright, so the memory bound is
  asserted on Linux only.

Building the per-version venv shells out to ``uv``; the first build needs
network access to install ``snackbase_fn`` and its ``httpx`` dependency. This
mirrors ``tests/unit/test_function_runner.py``, which already carries that cost.
"""

from __future__ import annotations

import socket
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from snackbase.infrastructure.functions.env_builder import build_function_env, compute_version_sha
from snackbase.infrastructure.functions.runner import FunctionRunner
from snackbase.infrastructure.functions.sandbox import sandbox_available

requires_sandbox = pytest.mark.skipif(
    not sandbox_available(),
    reason="filesystem confinement requires Landlock (Linux 5.13+)",
)
requires_rlimit_as = pytest.mark.skipif(
    sys.platform != "linux",
    reason="macOS rejects setrlimit(RLIMIT_AS); the bound applies on the Linux runtime",
)

HOST_FILE_MARKER = "HOST-DB-SECRET"
OTHER_TENANT_MARKER = "OTHER-TENANT-SECRET"

READ_PATH_HANDLER = '''
from snackbase_fn import Response

def handler(req):
    target = req.json.get("target")
    try:
        with open(target, "r") as fh:
            return Response.json({"read": True, "content": fh.read()})
    except Exception as exc:
        return Response.json({"read": False, "error": type(exc).__name__})
'''

RAW_SOCKET_HANDLER = '''
import socket

from snackbase_fn import Response

def handler(req):
    host = req.json["host"]
    port = req.json["port"]
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return Response.json({"connected": True, "blocked": False})
    except Exception as exc:
        return Response.json({"connected": False, "blocked": True, "error": type(exc).__name__})
'''

HTTPX_EGRESS_HANDLER = '''
import httpx

from snackbase_fn import Response

def handler(req):
    try:
        with httpx.Client(timeout=2) as client:
            client.get(req.json["url"])
        return Response.json({"blocked": False})
    except Exception as exc:
        return Response.json({"blocked": True, "error": type(exc).__name__})
'''

RLIMIT_PROBE_HANDLER = '''
import resource

from snackbase_fn import Response

def handler(req):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    return Response.json({"soft": soft, "hard": hard, "infinity": resource.RLIM_INFINITY})
'''

# Bounded on purpose: enough allocation to model a runaway handler, capped so a
# CI runner is never actually driven to OOM.
RUNAWAY_ALLOC_HANDLER = '''
import time

from snackbase_fn import Response

def handler(req):
    blocks = []
    for _ in range(200):
        blocks.append(bytearray(1024 * 1024))
        time.sleep(0.01)
    return Response.json({"allocated": len(blocks)})
'''

HELLO_HANDLER = '''
from snackbase_fn import Response

def handler(req):
    return Response.json({"ok": True})
'''


@pytest.fixture(scope="module")
def sandbox_envs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Two function envs under one base path, owned by different accounts."""
    base = tmp_path_factory.mktemp("fn_sandbox_envs")
    sha = compute_version_sha({"handler.py": HELLO_HANDLER}, [])

    victim_env = build_function_env(
        base_path=base,
        account_id="acct-victim",
        function_id="fn-victim",
        version_sha=sha,
        dependencies=[],
        python_executable=sys.executable,
    )
    (victim_env / "tenant_secret.txt").write_text(OTHER_TENANT_MARKER)

    attacker_env = build_function_env(
        base_path=base,
        account_id="acct-attacker",
        function_id="fn-attacker",
        version_sha=sha,
        dependencies=[],
        python_executable=sys.executable,
    )

    return {"base": base, "attacker": attacker_env, "victim": victim_env}


def _invoke(
    env_path: Path, source: str, body: dict[str, Any], *, timeout: int = 20
) -> Any:
    runner = FunctionRunner(timeout_seconds=timeout)
    return runner.invoke(
        env_path=env_path,
        source_files={"handler.py": source},
        entrypoint="handler.py",
        request_payload={"method": "POST", "path": "/", "headers": {}, "json": body},
    )


# ---------------------------------------------------------------------------
# Filesystem confinement
# ---------------------------------------------------------------------------


@requires_sandbox
def test_fn_sbx_001_cannot_read_host_state_file(
    sandbox_envs: dict[str, Path], tmp_path: Path
) -> None:
    """FN-SBX-001: a handler cannot read host state outside its env.

    Stands in for the SQLite database file, which lives at a path the handler
    can trivially guess from `SNACKBASE_DATABASE_URL` conventions.
    """
    host_state = tmp_path / "snackbase.db"
    host_state.write_text(HOST_FILE_MARKER)

    result = _invoke(
        sandbox_envs["attacker"], READ_PATH_HANDLER, {"target": str(host_state)}
    )

    assert result.status == "success", result.error_message
    assert result.body["read"] is False, "handler read a host file outside its sandbox"
    assert HOST_FILE_MARKER not in str(result.body)


@requires_sandbox
def test_fn_sbx_002_cannot_read_other_tenants_function_env(
    sandbox_envs: dict[str, Path],
) -> None:
    """FN-SBX-002: a handler cannot read another account's function env."""
    victim_file = sandbox_envs["victim"] / "tenant_secret.txt"

    result = _invoke(
        sandbox_envs["attacker"], READ_PATH_HANDLER, {"target": str(victim_file)}
    )

    assert result.status == "success", result.error_message
    assert result.body["read"] is False, "handler read another tenant's function env"
    assert OTHER_TENANT_MARKER not in str(result.body)


# ---------------------------------------------------------------------------
# Egress
# ---------------------------------------------------------------------------


@pytest.fixture
def loopback_listener() -> Iterator[int]:
    """A local TCP listener standing in for a disallowed internal destination.

    Loopback is denied by ``classify_url``, so reaching it proves the egress
    policy was bypassed — without depending on real network conditions.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    port = server.getsockname()[1]

    stop = threading.Event()

    def _accept_loop() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = server.accept()
            except OSError:
                continue
            conn.close()

    thread = threading.Thread(target=_accept_loop, daemon=True)
    thread.start()

    yield port

    stop.set()
    thread.join(timeout=2)
    server.close()


def test_fn_sbx_010_raw_socket_egress_is_blocked(
    sandbox_envs: dict[str, Path], loopback_listener: int
) -> None:
    """FN-SBX-010: raw sockets must be subject to the egress policy."""
    result = _invoke(
        sandbox_envs["attacker"],
        RAW_SOCKET_HANDLER,
        {"host": "127.0.0.1", "port": loopback_listener},
    )

    assert result.status == "success", result.error_message
    assert result.body["blocked"] is True, (
        "raw socket reached a denied destination — the egress policy only "
        "patches httpx and urllib"
    )


def test_fn_sbx_011_httpx_egress_to_metadata_is_blocked(
    sandbox_envs: dict[str, Path],
) -> None:
    """FN-SBX-011: regression — the httpx egress guard still blocks metadata IPs."""
    result = _invoke(
        sandbox_envs["attacker"],
        HTTPX_EGRESS_HANDLER,
        {"url": "http://169.254.169.254/latest/meta-data/"},
    )

    assert result.status == "success", result.error_message
    assert result.body["blocked"] is True


# ---------------------------------------------------------------------------
# Secret scrubbing — this one already works; lock it in
# ---------------------------------------------------------------------------


def test_fn_sbx_020_child_env_excludes_master_secrets() -> None:
    """FN-SBX-020: the invoke child env never carries the host master secrets."""
    runner = FunctionRunner(timeout_seconds=5)

    child_env = runner._build_child_env(
        {
            "SNACKBASE_SECRET_KEY": "host-secret-key",
            "SNACKBASE_ENCRYPTION_KEY": "host-encryption-key",
            "SNACKBASE_DATABASE_URL": "postgresql+asyncpg://user:pass@db/prod",
            "FN_SLUG": "probe",
        },
        "exec-1",
    )

    assert "SNACKBASE_SECRET_KEY" not in child_env
    assert "SNACKBASE_ENCRYPTION_KEY" not in child_env
    assert "SNACKBASE_DATABASE_URL" not in child_env
    assert child_env["FN_SLUG"] == "probe"
    assert "host-secret-key" not in child_env.values()


# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------


@requires_rlimit_as
def test_fn_sbx_030_child_process_has_address_space_limit(
    sandbox_envs: dict[str, Path],
) -> None:
    """FN-SBX-030: the invoke child must run under a memory bound."""
    result = _invoke(sandbox_envs["attacker"], RLIMIT_PROBE_HANDLER, {})

    assert result.status == "success", result.error_message
    assert result.body["soft"] != result.body["infinity"], (
        "RLIMIT_AS is unlimited — a runaway handler is bounded only by wall clock"
    )


def test_fn_sbx_031_runaway_allocation_is_killed_and_runner_survives(
    sandbox_envs: dict[str, Path],
) -> None:
    """FN-SBX-031: a runaway handler is terminated and the next invoke still works."""
    result = _invoke(
        sandbox_envs["attacker"], RUNAWAY_ALLOC_HANDLER, {}, timeout=2
    )

    assert result.status == "timeout"
    assert result.http_status == 504

    follow_up = _invoke(sandbox_envs["attacker"], HELLO_HANDLER, {})
    assert follow_up.status == "success", follow_up.error_message
    assert follow_up.body == {"ok": True}
