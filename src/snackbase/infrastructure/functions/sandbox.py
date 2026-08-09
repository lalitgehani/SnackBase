"""OS-level confinement for function invocations.

Tenant handlers are arbitrary Python running on the host. No in-process guard
can bound them — a handler can always re-import `os`, or reach the syscall
through `ctypes`. Containment therefore has to come from the kernel:

* **Filesystem** — the invoke child is restricted with `Landlock`, so the only
  paths it can reach are the interpreter it runs on, its own function env
  (read-only) and its per-invoke work directory (read-write). Other tenants'
  envs, ``sb_data/`` and the database file are unreachable, and the restriction
  survives ``execve`` and every re-import a handler might attempt.
* **Resources** — ``setrlimit`` bounds address space, CPU time and open files,
  so a runaway handler is stopped by the kernel rather than only by the
  runner's wall clock.

Landlock was chosen over a namespace sandbox (bubblewrap, nsjail) because it
needs no privileges at all: no `CAP_SYS_ADMIN`, no user namespaces, no seccomp
exemption. Those are exactly what a container runtime withholds by default, so
a namespace sandbox would have forced every deployment to loosen its container
settings to run functions at all.

Landlock is Linux 5.13+. On other platforms the mode resolves to unsandboxed so
local development keeps working; production treats a missing kernel feature as
a hard failure rather than silently degrading (see `resolve_sandbox_mode`).
"""

from __future__ import annotations

import ctypes
import os
import resource
import struct
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from snackbase.core.config import Settings, get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

# Landlock UAPI — linux/landlock.h
_NR_CREATE_RULESET = 444
_NR_ADD_RULE = 445
_NR_RESTRICT_SELF = 446
_CREATE_RULESET_VERSION = 1 << 0
_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38

_ACCESS_EXECUTE = 1 << 0
_ACCESS_WRITE_FILE = 1 << 1
_ACCESS_READ_FILE = 1 << 2
_ACCESS_READ_DIR = 1 << 3
_ACCESS_REMOVE_DIR = 1 << 4
_ACCESS_REMOVE_FILE = 1 << 5
_ACCESS_MAKE_CHAR = 1 << 6
_ACCESS_MAKE_DIR = 1 << 7
_ACCESS_MAKE_REG = 1 << 8
_ACCESS_MAKE_SOCK = 1 << 9
_ACCESS_MAKE_FIFO = 1 << 10
_ACCESS_MAKE_BLOCK = 1 << 11
_ACCESS_MAKE_SYM = 1 << 12
_ACCESS_REFER = 1 << 13  # ABI 2
_ACCESS_TRUNCATE = 1 << 14  # ABI 3
_ACCESS_IOCTL_DEV = 1 << 15  # ABI 5

# Linux-only open flag; the constant is absent from `os` on other platforms,
# where no ruleset is ever built.
_O_PATH = getattr(os, "O_PATH", 0o010000000)

# Every right the running kernel understands has to be *handled*, because
# anything left out of the ruleset stays permitted everywhere.
_HANDLED_BY_ABI = {
    1: (1 << 13) - 1,
    2: (1 << 14) - 1,
    3: (1 << 15) - 1,
    4: (1 << 15) - 1,
}
_HANDLED_LATEST = (1 << 16) - 1

_READ_ACCESS = _ACCESS_READ_FILE | _ACCESS_READ_DIR | _ACCESS_EXECUTE
_WRITE_ACCESS = (
    _READ_ACCESS
    | _ACCESS_WRITE_FILE
    | _ACCESS_MAKE_REG
    | _ACCESS_MAKE_DIR
    | _ACCESS_MAKE_SYM
    | _ACCESS_MAKE_SOCK
    | _ACCESS_MAKE_FIFO
    | _ACCESS_REMOVE_FILE
    | _ACCESS_REMOVE_DIR
    | _ACCESS_TRUNCATE
    | _ACCESS_REFER
)

# Read-only host paths the interpreter needs. Missing entries are skipped, so
# this covers both merged-/usr distributions and older layouts.
_SYSTEM_PATHS = (
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/lib64",
    "/etc",
    "/proc",
    "/dev",
)


class SandboxUnavailableError(RuntimeError):
    """Raised when confinement is required but cannot be established."""


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def landlock_abi() -> int:
    """Return the kernel's Landlock ABI version, or 0 when unsupported."""
    if sys.platform != "linux":
        return 0
    try:
        abi = _libc().syscall(_NR_CREATE_RULESET, None, 0, _CREATE_RULESET_VERSION)
    except (OSError, AttributeError):  # pragma: no cover — no libc syscall shim
        return 0
    return abi if abi > 0 else 0


def sandbox_available() -> bool:
    """True when this kernel can enforce filesystem confinement."""
    return landlock_abi() > 0


def resolve_sandbox_mode(settings: Settings | None = None) -> str:
    """Return the effective mode: ``required`` or ``disabled``.

    ``auto`` means "confine wherever the kernel supports it" in development, and
    "confine or refuse" in production — an operator who never deploys functions
    is unaffected either way, because the check happens per invoke.
    """
    settings = settings or get_settings()
    mode = settings.function_sandbox_mode
    if mode != "auto":
        return mode
    if settings.is_production:
        return "required"
    return "required" if sandbox_available() else "disabled"


def log_sandbox_posture(settings: Settings | None = None) -> str:
    """Report the effective confinement at startup and return the mode."""
    settings = settings or get_settings()
    mode = resolve_sandbox_mode(settings)
    abi = landlock_abi()

    if mode == "disabled":
        logger.warning(
            "Functions sandbox: DISABLED — invoked handlers can read the host filesystem",
            configured_mode=settings.function_sandbox_mode,
        )
    elif abi:
        logger.info("Functions sandbox: enabled", mechanism="landlock", abi=abi)
    else:
        logger.error(
            "Functions sandbox: REQUIRED but this kernel has no Landlock support — "
            "function invocations will be refused. Run on Linux 5.13+, or set "
            "SNACKBASE_FUNCTION_SANDBOX_MODE=disabled to run them unconfined.",
            configured_mode=settings.function_sandbox_mode,
        )
    return mode


class FilesystemConfinement:
    """A prepared Landlock ruleset, applied by the invoke child at exec time.

    The ruleset is built in the parent — creating it and adding rules restricts
    nobody — so the pre-exec hook only has two syscalls left to make. That keeps
    the post-fork window free of allocation and locking, which is the standard
    hazard with ``preexec_fn``.
    """

    def __init__(self, ruleset_fd: int) -> None:
        self.fd = ruleset_fd

    def apply(self) -> None:
        """Enforce the ruleset on the calling process. Runs post-fork."""
        libc = _libc()
        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS failed")
        if libc.syscall(_NR_RESTRICT_SELF, self.fd, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self failed")

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def create_filesystem_confinement(
    *, env_root: Path, workdir: Path, mode: str
) -> FilesystemConfinement | None:
    """Build the ruleset confining an invoke to its own env and work directory.

    Args:
        env_root: The function version's virtualenv — readable and executable.
        workdir: The per-invoke directory holding the handler source, writable
            because the bootstrap and the handler write into it.
        mode: The resolved mode from `resolve_sandbox_mode`.

    Returns:
        The prepared confinement, or None when confinement is disabled.

    Raises:
        SandboxUnavailableError: If confinement is required but the kernel
            cannot provide it. Failing the invoke is the point — running the
            handler unconfined would hand a tenant the host filesystem.
    """
    if mode == "disabled":
        return None

    abi = landlock_abi()
    if abi == 0:
        raise SandboxUnavailableError(
            "Function invocations require Landlock filesystem confinement, which this "
            "kernel does not provide (Linux 5.13+ is needed). Set "
            "SNACKBASE_FUNCTION_SANDBOX_MODE=disabled to run functions unconfined."
        )

    read_only: list[Path] = [Path(p) for p in _SYSTEM_PATHS if os.path.exists(p)]
    # The venv's bin/python links to the interpreter that created it, which need
    # not live under /usr — a uv-managed Python sits under the operator's home.
    base_prefix = _venv_base_prefix(env_root)
    if base_prefix is not None:
        read_only.append(base_prefix)
    read_only.append(env_root)

    return _build_ruleset(abi, read_only=read_only, read_write=[workdir])


def _build_ruleset(
    abi: int, *, read_only: Sequence[Path], read_write: Sequence[Path]
) -> FilesystemConfinement:
    libc = _libc()
    handled = _HANDLED_BY_ABI.get(abi, _HANDLED_LATEST)

    # struct landlock_ruleset_attr { __u64 handled_access_fs; }
    attr = struct.pack("=Q", handled)
    buf = ctypes.create_string_buffer(attr, len(attr))
    ruleset_fd = libc.syscall(_NR_CREATE_RULESET, buf, len(attr), 0)
    if ruleset_fd < 0:
        raise SandboxUnavailableError(
            f"landlock_create_ruleset failed: {os.strerror(ctypes.get_errno())}"
        )

    confinement = FilesystemConfinement(ruleset_fd)
    try:
        for path in read_only:
            _add_path_rule(libc, ruleset_fd, path, _READ_ACCESS & handled)
        for path in read_write:
            _add_path_rule(libc, ruleset_fd, path, _WRITE_ACCESS & handled)
    except Exception:
        confinement.close()
        raise
    return confinement


def _add_path_rule(libc: ctypes.CDLL, ruleset_fd: int, path: Path, access: int) -> None:
    try:
        path_fd = os.open(str(path), _O_PATH | os.O_CLOEXEC)
    except OSError:
        return  # A path that does not exist needs no rule.
    try:
        # struct landlock_path_beneath_attr { __u64 allowed_access; __s32 parent_fd; }
        # — packed, hence 12 bytes rather than 16.
        rule = struct.pack("=Qi", access, path_fd)
        buf = ctypes.create_string_buffer(rule, len(rule))
        if libc.syscall(_NR_ADD_RULE, ruleset_fd, _RULE_PATH_BENEATH, buf, 0) != 0:
            raise SandboxUnavailableError(
                f"landlock_add_rule failed for {path}: "
                f"{os.strerror(ctypes.get_errno())}"
            )
    finally:
        os.close(path_fd)


def _venv_base_prefix(env_root: Path) -> Path | None:
    """Installation prefix of the interpreter this virtualenv was created from."""
    config = env_root / "pyvenv.cfg"
    if config.exists():
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "home" and value.strip():
                # `home` is the base interpreter's bin directory.
                return Path(value.strip()).resolve().parent

    python = env_root / "bin" / "python"
    if python.exists():
        return python.resolve().parent.parent
    return None


def resource_limit_hook(
    *, memory_mb: int, cpu_seconds: int, max_open_files: int = 512
) -> Callable[[], None] | None:
    """Build the resource half of the pre-exec hook.

    Deliberately not `RLIMIT_NPROC`: it counts processes per real uid, not per
    process tree, and on Linux threads count against it — so a value low enough
    to matter breaks ordinary handlers, and the correct tool for that bound is
    the pid cgroup controller.
    """
    if os.name != "posix":
        return None

    limits: list[tuple[int, int]] = [
        (resource.RLIMIT_AS, memory_mb * 1024 * 1024),
        (resource.RLIMIT_CPU, cpu_seconds),
        (resource.RLIMIT_NOFILE, max_open_files),
    ]

    def _apply() -> None:
        for what, soft in limits:
            try:
                _, hard = resource.getrlimit(what)
                if hard != resource.RLIM_INFINITY:
                    soft = min(soft, hard)
                resource.setrlimit(what, (soft, hard))
            except (ValueError, OSError):
                # A limit the platform will not accept must not stop the invoke;
                # the remaining limits still apply.
                continue

    return _apply


def preexec_hook(
    *, confinement: FilesystemConfinement | None, limits: Callable[[], None] | None
) -> Callable[[], None] | None:
    """Combine confinement and resource limits into one ``preexec_fn``."""
    if confinement is None and limits is None:
        return None

    def _apply() -> None:
        if limits is not None:
            limits()
        if confinement is not None:
            confinement.apply()

    return _apply
