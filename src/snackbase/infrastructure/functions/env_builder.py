"""Build per-version function virtualenvs with uv."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class EnvBuildError(RuntimeError):
    """Raised when uv venv/install fails."""

    def __init__(self, message: str, *, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


def compute_version_sha(source_files: dict[str, str], dependencies: Sequence[str]) -> str:
    """Deterministic content hash for source + dependencies."""
    payload = {
        "files": {k: source_files[k] for k in sorted(source_files.keys())},
        "deps": list(dependencies),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def total_source_bytes(source_files: dict[str, str]) -> int:
    return sum(len(v.encode("utf-8")) for v in source_files.values())


def _snackbase_fn_package_root() -> Path:
    """Locate the installable snackbase_fn package root (has pyproject.toml)."""
    # Preferred: packages/snackbase_fn next to the SnackBase project root
    here = Path(__file__).resolve()
    candidates = [
        here.parents[4] / "packages" / "snackbase_fn",  # .../SnackBase/packages/snackbase_fn
        here.parents[3] / "packages" / "snackbase_fn",
        Path.cwd() / "packages" / "snackbase_fn",
    ]
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists():
            return candidate
    # Fallback: copy from importable snackbase_fn into a temp layout is not needed
    # if the packages tree is present; raise a clear error otherwise.
    raise EnvBuildError(
        "Cannot locate packages/snackbase_fn for function env install. "
        "Ensure SnackBase/packages/snackbase_fn exists."
    )


# Variables `uv` legitimately needs: where to find tools, where to cache, how to
# reach the index through a proxy, and which CA bundle to trust. Everything else
# — above all `SNACKBASE_*` — is withheld, so a build backend that does run has
# no host secrets to read.
_BUILD_ENV_PASSTHROUGH = (
    "PATH",
    "HOME",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)


def build_install_env() -> dict[str, str]:
    """Environment for the `uv` subprocesses that build a function env.

    Dependency installs execute third-party code on the host (a build backend,
    or a wheel's own metadata hooks), so the host environment — which carries
    `SNACKBASE_SECRET_KEY`, `SNACKBASE_ENCRYPTION_KEY` and
    `SNACKBASE_DATABASE_URL` — must not be inherited.
    """
    env = {
        key: os.environ[key] for key in _BUILD_ENV_PASSTHROUGH if key in os.environ
    }
    env.setdefault("PATH", "/usr/bin:/bin")
    env["UV_NO_PROGRESS"] = "1"
    for key, value in os.environ.items():
        if key.startswith("UV_") and key != "UV_NO_PROGRESS":
            env[key] = value
    return env


def build_function_env(
    *,
    base_path: str | Path,
    account_id: str,
    function_id: str,
    version_sha: str,
    dependencies: Sequence[str],
    python_executable: str | None = None,
) -> Path:
    """Create a venv and install baseline + user pins via uv.

    Returns the env path. Reuses an existing env directory when present
    (deterministic by version_sha).
    """
    env_root = Path(base_path) / account_id / function_id / version_sha
    # Always return/store absolute paths so subprocess runners that chdir into a
    # temp workdir can still exec bin/python (relative env paths break on Popen).
    if not env_root.is_absolute():
        env_root = (Path.cwd() / env_root).resolve()
    else:
        env_root = env_root.resolve()

    if env_root.exists() and (env_root / "bin" / "python").exists():
        logger.info("Reusing function env", env_path=str(env_root))
        return env_root

    env_root.parent.mkdir(parents=True, exist_ok=True)
    # Clean partial builds
    if env_root.exists():
        shutil.rmtree(env_root, ignore_errors=True)

    python = python_executable or sys.executable
    uv = shutil.which("uv")
    if not uv:
        raise EnvBuildError("uv is not installed on the host; required for function deploys")

    build_env = build_install_env()

    try:
        subprocess.run(
            [uv, "venv", str(env_root), "--python", python],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
            env=build_env,
        )
    except subprocess.CalledProcessError as exc:
        raise EnvBuildError(
            "Failed to create function venv",
            stderr=(exc.stderr or "")[-2000:],
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise EnvBuildError("Timed out creating function venv") from exc

    env_python = str(env_root / "bin" / "python")
    pins = list(dependencies)

    # Two installs, because only first-party code may run a build backend.
    # snackbase_fn is a local source tree and has to be built; tenant pins are
    # wheel-only, so no attacker-supplied `setup.py` ever executes on the host.
    steps: list[tuple[str, list[str]]] = [
        (
            "baseline runtime",
            [uv, "pip", "install", "--python", env_python,
             str(_snackbase_fn_package_root())],
        )
    ]
    if pins:
        steps.append(
            (
                "dependencies",
                [uv, "pip", "install", "--python", env_python,
                 "--only-binary", ":all:", *pins],
            )
        )

    for what, args in steps:
        try:
            proc = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
                env=build_env,
            )
        except subprocess.CalledProcessError as exc:
            shutil.rmtree(env_root, ignore_errors=True)
            raise EnvBuildError(
                f"Failed to install function {what}",
                stderr=(exc.stderr or "")[-2000:],
            ) from exc
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(env_root, ignore_errors=True)
            raise EnvBuildError(f"Timed out installing function {what}") from exc

    logger.info(
        "Function env built",
        env_path=str(env_root),
        deps=pins,
        stdout_tail=(proc.stdout or "")[-500:],
    )

    return env_root


def remove_function_env(env_path: str | Path | None) -> None:
    """Delete a version env directory if present."""
    if not env_path:
        return
    path = Path(env_path)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
