"""Active-operation guard: at most one backup or restore in flight at a time.

State lives in an in-process ``asyncio.Lock`` plus a lock file at
``<backup_dir>/.active`` claimed with ``O_CREAT | O_EXCL`` so the check and
the claim are one atomic filesystem operation. Nothing is written to the
database on purpose: a backup that recorded its own progress in the database
it is snapshotting would capture a job stuck in ``running`` that returns on
every restore.
"""

import asyncio
import contextlib
import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from snackbase.infrastructure.backup.destinations import DEFAULT_BACKUP_DIR, BackupInProgressError

if TYPE_CHECKING:
    pass

LOCK_FILENAME = ".active"


def _lock_path(backup_dir: Path | str | None) -> Path:
    return Path(backup_dir or DEFAULT_BACKUP_DIR) / LOCK_FILENAME


def _read_lock_file(path: Path) -> dict[str, Any] | None:
    """Parse the lock file, returning None when absent or unreadable."""
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, json.JSONDecodeError):
        return None


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def sweep_stale_lock(backup_dir: Path | str | None = None) -> bool:
    """Remove a lock file whose recorded PID is no longer running.

    A crash mid-backup must not wedge the feature permanently. Called at
    startup and before acquisition attempts. Returns whether a stale lock
    was removed.
    """
    path = _lock_path(backup_dir)
    info = _read_lock_file(path)
    if info is None:
        # Absent or garbage: a garbage file would block every future
        # operation, so remove it too.
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False
    try:
        pid = int(info.get("pid", 0))
    except (TypeError, ValueError):
        pid = 0
    if _pid_running(pid):
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def active_operation(backup_dir: Path | str | None = None) -> dict[str, Any] | None:
    """Report the in-flight operation without attempting to acquire.

    Returns the lock file contents, or None when nothing is in flight. A
    lock file naming a dead PID is treated as no operation (it is stale).
    """
    info = _read_lock_file(_lock_path(backup_dir))
    if info is None:
        return None
    try:
        pid = int(info.get("pid", 0))
    except (TypeError, ValueError):
        pid = 0
    if not _pid_running(pid):
        return None
    return info


_process_lock: asyncio.Lock = asyncio.Lock()
_process_lock_loop: asyncio.AbstractEventLoop | None = None


def _get_process_lock() -> asyncio.Lock:
    """The in-process lock, rebuilt when the running loop changes.

    Production runs a single loop so the lock persists; tests (and any
    embedder) that create successive loops must not inherit a lock bound
    to a dead one.
    """
    global _process_lock, _process_lock_loop
    loop = asyncio.get_running_loop()
    if _process_lock_loop is not loop:
        _process_lock = asyncio.Lock()
        _process_lock_loop = loop
    return _process_lock


@contextlib.asynccontextmanager
async def backup_lock(
    name: str,
    operation: str,
    backup_dir: Path | str | None = None,
) -> AsyncIterator[None]:
    """Hold the single-slot backup/restore slot for the duration of an operation.

    Args:
        name: Archive name the operation works on.
        operation: ``"backup"`` or ``"restore"``.
        backup_dir: Directory for the lock file; defaults to the standard
            local backup directory, which every process can see.

    Raises:
        BackupInProgressError: When another backup or restore is in flight,
            carrying that operation's kind and archive name.
    """
    path = _lock_path(backup_dir)
    # The process lock guards only the check-and-claim so concurrent tasks
    # serialise their filesystem race; the file itself is held for the
    # duration of the operation.
    async with _get_process_lock():
        await asyncio.to_thread(sweep_stale_lock, backup_dir)
        payload = {
            "operation": operation,
            "name": name,
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        try:
            existing = await asyncio.to_thread(_read_lock_file, path)
            if existing is not None:
                raise BackupInProgressError(
                    operation=str(existing.get("operation", "unknown")),
                    name=str(existing.get("name", "unknown")),
                )
            Path(path.parent).mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except BackupInProgressError:
            raise
        except OSError as exc:
            if getattr(exc, "errno", None) == 17:  # EEXIST: lost the race
                existing = await asyncio.to_thread(_read_lock_file, path)
                raise BackupInProgressError(
                    operation=str((existing or {}).get("operation", "unknown")),
                    name=str((existing or {}).get("name", "unknown")),
                ) from exc
            raise
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            await asyncio.to_thread(path.unlink)


def is_backup_in_progress_error(exc: BaseException) -> bool:
    """Type check helper so callers need not import the error separately."""
    return isinstance(exc, BackupInProgressError)
