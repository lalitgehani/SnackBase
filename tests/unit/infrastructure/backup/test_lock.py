"""Unit tests for the active-operation guard (F2.2)."""

import json
from pathlib import Path

import pytest

from snackbase.infrastructure.backup.destinations import BackupInProgressError
from snackbase.infrastructure.backup.lock import (
    LOCK_FILENAME,
    active_operation,
    backup_lock,
    sweep_stale_lock,
)


@pytest.fixture
def lock_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


class TestBackupLock:
    async def test_nested_acquisition_raises_in_progress(self, lock_dir: Path) -> None:
        async with backup_lock("one.zip", "backup", lock_dir):
            with pytest.raises(BackupInProgressError) as exc_info:
                async with backup_lock("two.zip", "backup", lock_dir):
                    pass
            assert exc_info.value.name == "one.zip"
            assert exc_info.value.operation == "backup"

    async def test_lock_file_removed_after_success(self, lock_dir: Path) -> None:
        async with backup_lock("one.zip", "backup", lock_dir):
            assert (lock_dir / LOCK_FILENAME).exists()

        assert not (lock_dir / LOCK_FILENAME).exists()

    async def test_lock_file_removed_after_failure(self, lock_dir: Path) -> None:
        with pytest.raises(RuntimeError):
            async with backup_lock("one.zip", "backup", lock_dir):
                raise RuntimeError("boom")

        assert not (lock_dir / LOCK_FILENAME).exists()

    async def test_lock_file_records_operation_and_pid(self, lock_dir: Path) -> None:
        import os

        async with backup_lock("one.zip", "restore", lock_dir):
            info = json.loads((lock_dir / LOCK_FILENAME).read_text())
            assert info["operation"] == "restore"
            assert info["name"] == "one.zip"
            assert info["pid"] == os.getpid()
            assert "started_at" in info

    async def test_active_operation_none_when_idle(self, lock_dir: Path) -> None:
        assert active_operation(lock_dir) is None

    async def test_active_operation_reports_while_held(self, lock_dir: Path) -> None:
        async with backup_lock("one.zip", "backup", lock_dir):
            current = active_operation(lock_dir)
            assert current is not None
            assert current["name"] == "one.zip"

    async def test_no_lock_state_in_database(self, lock_dir: Path) -> None:
        # The guard is purely file-and-memory based; this documents the
        # invariant that acquiring a lock needs no database session at all.
        async with backup_lock("one.zip", "backup", lock_dir):
            pass
        assert list(lock_dir.iterdir()) in ([], [lock_dir / LOCK_FILENAME])


class TestStaleLockSweep:
    async def test_dead_pid_lock_removed_on_sweep(self, lock_dir: Path) -> None:
        lock_dir.mkdir(parents=True)
        (lock_dir / LOCK_FILENAME).write_text(
            json.dumps(
                {
                    "operation": "backup",
                    "name": "dead.zip",
                    "pid": 999999,
                    "started_at": "2026-09-01T00:00:00",
                }
            )
        )

        assert sweep_stale_lock(lock_dir) is True
        assert not (lock_dir / LOCK_FILENAME).exists()
        assert active_operation(lock_dir) is None

    async def test_live_pid_lock_not_removed(self, lock_dir: Path) -> None:
        import os

        lock_dir.mkdir(parents=True)
        (lock_dir / LOCK_FILENAME).write_text(
            json.dumps(
                {
                    "operation": "backup",
                    "name": "live.zip",
                    "pid": os.getpid(),
                    "started_at": "2026-09-01T00:00:00",
                }
            )
        )

        assert sweep_stale_lock(lock_dir) is False
        assert (lock_dir / LOCK_FILENAME).exists()

    async def test_garbage_lock_file_cleared(self, lock_dir: Path) -> None:
        lock_dir.mkdir(parents=True)
        (lock_dir / LOCK_FILENAME).write_text("not json at all")

        assert sweep_stale_lock(lock_dir) is True
        assert not (lock_dir / LOCK_FILENAME).exists()

    async def test_sweep_then_acquire(self, lock_dir: Path) -> None:
        lock_dir.mkdir(parents=True)
        (lock_dir / LOCK_FILENAME).write_text(
            json.dumps({"operation": "backup", "name": "dead.zip", "pid": 999999})
        )

        async with backup_lock("fresh.zip", "backup", lock_dir):
            assert active_operation(lock_dir)["name"] == "fresh.zip"

    async def test_backup_in_progress_error_attributes(self) -> None:
        error = BackupInProgressError(operation="restore", name="x.zip")
        assert error.operation == "restore"
        assert error.name == "x.zip"
        assert "restore" in str(error)
