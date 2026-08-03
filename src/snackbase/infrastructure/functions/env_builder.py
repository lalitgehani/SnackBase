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

    try:
        subprocess.run(
            [uv, "venv", str(env_root), "--python", python],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise EnvBuildError(
            "Failed to create function venv",
            stderr=(exc.stderr or "")[-2000:],
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise EnvBuildError("Timed out creating function venv") from exc

    # Install baseline packages (snackbase_fn ships httpx as dependency)
    snackbase_fn_root = _snackbase_fn_package_root()
    pins = list(dependencies)
    install_args = [
        uv,
        "pip",
        "install",
        "--python",
        str(env_root / "bin" / "python"),
        str(snackbase_fn_root),
        *pins,
    ]
    try:
        proc = subprocess.run(
            install_args,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "UV_NO_PROGRESS": "1"},
        )
        logger.info(
            "Function env built",
            env_path=str(env_root),
            deps=list(pins),
            stdout_tail=(proc.stdout or "")[-500:],
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(env_root, ignore_errors=True)
        raise EnvBuildError(
            "Failed to install function dependencies",
            stderr=(exc.stderr or "")[-2000:],
        ) from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(env_root, ignore_errors=True)
        raise EnvBuildError("Timed out installing function dependencies") from exc

    return env_root


def remove_function_env(env_path: str | Path | None) -> None:
    """Delete a version env directory if present."""
    if not env_path:
        return
    path = Path(env_path)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
