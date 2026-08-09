"""FN-POL-*: the confinement policy itself (C-04b).

`test_sandbox_isolation.py` proves what a handler can and cannot do, but those
checks only run where the kernel provides Landlock. These tests cover the
decisions that must hold everywhere: how the mode resolves, and that an
unavailable sandbox fails the invoke instead of quietly running the handler on
the bare host.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from snackbase.core.config import Settings
from snackbase.infrastructure.functions import sandbox
from snackbase.infrastructure.functions.sandbox import (
    SandboxUnavailableError,
    create_filesystem_confinement,
    preexec_hook,
    resolve_sandbox_mode,
    resource_limit_hook,
)

PROD_SECRETS = {
    "secret_key": "production-secret-key-value-32byt",
    "token_secret": "production-token-secret-32-bytes",
    "encryption_key": "production-encryption-key-value32",
}


def test_fn_pol_001_production_auto_requires_the_sandbox() -> None:
    """FN-POL-001: production never degrades to running handlers unconfined."""
    settings = Settings(environment="production", function_sandbox_mode="auto", **PROD_SECRETS)

    with patch.object(sandbox, "sandbox_available", return_value=False):
        assert resolve_sandbox_mode(settings) == "required"


def test_fn_pol_002_development_auto_follows_availability() -> None:
    """FN-POL-002: `auto` keeps local development working on kernels without Landlock."""
    settings = Settings(environment="development", function_sandbox_mode="auto")

    with patch.object(sandbox, "sandbox_available", return_value=False):
        assert resolve_sandbox_mode(settings) == "disabled"
    with patch.object(sandbox, "sandbox_available", return_value=True):
        assert resolve_sandbox_mode(settings) == "required"


def test_fn_pol_003_explicit_mode_is_never_overridden() -> None:
    """FN-POL-003: an operator's explicit choice wins in either direction."""
    disabled = Settings(
        environment="production", function_sandbox_mode="disabled", **PROD_SECRETS
    )
    required = Settings(environment="development", function_sandbox_mode="required")

    assert resolve_sandbox_mode(disabled) == "disabled"
    assert resolve_sandbox_mode(required) == "required"


def test_fn_pol_010_missing_kernel_support_fails_the_invoke(tmp_path: Path) -> None:
    """FN-POL-010: a required-but-unavailable sandbox refuses; it does not degrade."""
    with patch.object(sandbox, "landlock_abi", return_value=0):
        with pytest.raises(SandboxUnavailableError, match="Landlock"):
            create_filesystem_confinement(
                env_root=tmp_path / "env", workdir=tmp_path / "work", mode="required"
            )


def test_fn_pol_011_disabled_mode_builds_no_confinement(tmp_path: Path) -> None:
    """FN-POL-011: `disabled` is a pass-through with no kernel dependency."""
    assert (
        create_filesystem_confinement(
            env_root=tmp_path / "env", workdir=tmp_path / "work", mode="disabled"
        )
        is None
    )


def test_fn_pol_012_ruleset_covers_this_tenants_paths_only(tmp_path: Path) -> None:
    """FN-POL-012: the ruleset grants the env read-only, the workdir read-write.

    Asserted against the rules handed to the kernel, so it holds on hosts that
    cannot run Landlock and would otherwise skip every confinement check.
    """
    env_root = tmp_path / "envs" / "acct-a" / "fn" / "sha"
    workdir = tmp_path / "work"
    sibling = tmp_path / "envs" / "acct-b"
    for path in (env_root, workdir, sibling):
        path.mkdir(parents=True)

    granted: dict[str, int] = {}

    def _record(_libc: object, _fd: int, path: Path, access: int) -> None:
        granted[str(path)] = access

    with (
        patch.object(sandbox, "landlock_abi", return_value=5),
        patch.object(sandbox, "_add_path_rule", _record),
        patch.object(sandbox, "_libc") as libc,
    ):
        libc.return_value.syscall.return_value = 99
        confinement = create_filesystem_confinement(
            env_root=env_root, workdir=workdir, mode="required"
        )

    assert confinement is not None
    confinement.fd = -1  # never a real descriptor here

    assert str(env_root) in granted, "the function env must be reachable"
    assert not granted[str(env_root)] & sandbox._ACCESS_WRITE_FILE, (
        "the function env must be read-only"
    )
    assert granted[str(workdir)] & sandbox._ACCESS_WRITE_FILE, (
        "the work directory must be writable"
    )
    assert str(sibling) not in granted, "another tenant's env must not be granted"
    assert str(tmp_path / "envs") not in granted, (
        "granting the env base path would leave every tenant reachable"
    )


def test_fn_pol_020_resource_hook_bounds_address_space_and_cpu() -> None:
    """FN-POL-020: the pre-exec hook applies the limits it claims to."""
    applied: list[tuple[int, tuple[int, int]]] = []

    def _fake_setrlimit(what: int, limits: tuple[int, int]) -> None:
        applied.append((what, limits))

    hook = resource_limit_hook(memory_mb=256, cpu_seconds=35)
    assert hook is not None

    with patch.object(sandbox.resource, "setrlimit", _fake_setrlimit):
        hook()

    bounded = {what: limits[0] for what, limits in applied}
    assert bounded[sandbox.resource.RLIMIT_AS] == 256 * 1024 * 1024
    assert bounded[sandbox.resource.RLIMIT_CPU] == 35
    assert sandbox.resource.RLIMIT_NOFILE in bounded


def test_fn_pol_021_resource_hook_survives_a_rejected_limit() -> None:
    """FN-POL-021: a limit the platform refuses must not fail the whole invoke.

    macOS rejects `RLIMIT_AS` outright; the CPU and file-descriptor bounds still
    have to be applied.
    """
    applied: list[int] = []

    def _picky_setrlimit(what: int, limits: tuple[int, int]) -> None:
        if what == sandbox.resource.RLIMIT_AS:
            raise ValueError("current limit exceeds maximum limit")
        applied.append(what)

    hook = resource_limit_hook(memory_mb=256, cpu_seconds=35)
    assert hook is not None

    with patch.object(sandbox.resource, "setrlimit", _picky_setrlimit):
        hook()

    assert sandbox.resource.RLIMIT_CPU in applied
    assert sandbox.resource.RLIMIT_NOFILE in applied


def test_fn_pol_022_preexec_applies_limits_before_confinement() -> None:
    """FN-POL-022: limits are set first, since confinement is irreversible."""
    order: list[str] = []

    class _Confinement:
        def apply(self) -> None:
            order.append("confine")

    hook = preexec_hook(
        confinement=_Confinement(),  # type: ignore[arg-type]
        limits=lambda: order.append("limits"),
    )
    assert hook is not None
    hook()

    assert order == ["limits", "confine"]
