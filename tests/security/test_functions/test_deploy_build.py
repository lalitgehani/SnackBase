"""FN-BUILD-*: function deploy-time build isolation (C-04a).

Deploying a function shells out to ``uv pip install``. Installing a package can
execute code on the host — a source distribution's build backend runs
``setup.py``/PEP 517 hooks — and the deploy endpoint is gated to account
admin/owner, not superadmin. Two things therefore have to hold:

* the install subprocess must not inherit the host environment, which carries
  ``SNACKBASE_SECRET_KEY``, ``SNACKBASE_ENCRYPTION_KEY`` and
  ``SNACKBASE_DATABASE_URL``; and
* tenant-supplied pins must install from wheels only, so no attacker-authored
  build backend runs at all.

``FN-BUILD-020`` covers the third leg: an unconfigured deployment must not let
a tenant pull arbitrary packages from PyPI in the first place.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest

from snackbase.core.config import Settings
from snackbase.infrastructure.functions.env_builder import build_install_env

HOST_SECRETS = {
    "SNACKBASE_SECRET_KEY": "host-secret-key",
    "SNACKBASE_ENCRYPTION_KEY": "host-encryption-key",
    "SNACKBASE_DATABASE_URL": "postgresql+asyncpg://user:pass@db/prod",
    "AWS_SECRET_ACCESS_KEY": "host-aws-secret",
}


def test_fn_build_001_install_env_excludes_host_secrets() -> None:
    """FN-BUILD-001: the build subprocess env carries no host secrets."""
    with patch.dict(os.environ, {**HOST_SECRETS, "PATH": "/usr/bin:/bin"}, clear=True):
        env = build_install_env()

    for key in HOST_SECRETS:
        assert key not in env, f"{key} leaked into the function build environment"
    assert "host-secret-key" not in env.values()
    assert "host-aws-secret" not in env.values()


def test_fn_build_002_install_env_keeps_what_uv_needs() -> None:
    """FN-BUILD-002: proxy, CA and cache settings still reach uv."""
    with patch.dict(
        os.environ,
        {
            "PATH": "/usr/bin:/bin",
            "HTTPS_PROXY": "http://proxy.internal:3128",
            "SSL_CERT_FILE": "/etc/ssl/corp.pem",
            "UV_CACHE_DIR": "/var/cache/uv",
            **HOST_SECRETS,
        },
        clear=True,
    ):
        env = build_install_env()

    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HTTPS_PROXY"] == "http://proxy.internal:3128"
    assert env["SSL_CERT_FILE"] == "/etc/ssl/corp.pem"
    assert env["UV_CACHE_DIR"] == "/var/cache/uv"


def test_fn_build_010_tenant_pins_install_wheels_only(tmp_path: Any) -> None:
    """FN-BUILD-010: tenant pins are installed with --only-binary, so no sdist builds."""
    from snackbase.infrastructure.functions import env_builder

    calls: list[list[str]] = []

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(args: list[str], **kwargs: Any) -> _Completed:
        calls.append(args)
        # Materialise the venv python so build_function_env proceeds.
        if args[1] == "venv":
            bin_dir = tmp_path / "envs" / "acct" / "fn" / "sha" / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            (bin_dir / "python").write_text("#!/bin/sh\n")
        return _Completed()

    with patch.object(env_builder.subprocess, "run", _fake_run):
        env_builder.build_function_env(
            base_path=tmp_path / "envs",
            account_id="acct",
            function_id="fn",
            version_sha="sha",
            dependencies=["cowsay==6.1"],
        )

    pin_installs = [c for c in calls if "cowsay==6.1" in c]
    assert pin_installs, f"no install call carried the tenant pin: {calls}"
    for call in pin_installs:
        assert "--only-binary" in call, "tenant pins may build an sdist on the host"
        assert call[call.index("--only-binary") + 1] == ":all:"


def test_fn_build_020_dependency_mode_defaults_to_allowlist() -> None:
    """FN-BUILD-020: an unconfigured deployment refuses unknown packages."""
    assert Settings().function_dependency_mode == "allowlist"


@pytest.mark.parametrize("pin", ["cowsay==6.1", "requests==2.32.5"])
def test_fn_build_021_pins_outside_the_allowlist_are_refused(pin: str) -> None:
    """FN-BUILD-021: the default mode rejects any pin the operator did not allow."""
    from snackbase.infrastructure.functions.pin_parser import (
        PinParseError,
        parse_dependencies,
    )

    with pytest.raises(PinParseError, match="allowlist"):
        parse_dependencies([pin])
