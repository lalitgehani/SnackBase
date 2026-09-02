"""Unit tests for the pre-boot restore executor (F3.2, F3.3)."""

import json
import os
import sqlite3
import time
from pathlib import Path

import pytest

from snackbase.core.config import Settings
from snackbase.infrastructure.backup.archive import MANIFEST_MEMBER
from snackbase.infrastructure.backup.destinations import LocalBackupDestination
from snackbase.infrastructure.backup.manifest import BackupManifest, fingerprint
from snackbase.infrastructure.backup.restore import (
    AUDIT_PENDING_FILENAME,
    LAST_RESTORE_FILENAME,
    MARKER_FILENAME,
    RESTORE_OLD_DIRNAME,
    RestoreAbortedError,
    execute_pending_restore,
    pop_audit_pending,
    read_last_restore,
    read_marker,
    write_marker,
)
from snackbase.infrastructure.backup.service import create_backup


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'sb_data' / 'snackbase.db'}",
        storage_path=str(tmp_path / "sb_data" / "files"),
        _env_file=None,
        **overrides,  # type: ignore[arg-type]
    )


def _db_value(db_path: Path, table: str = "t") -> str:
    connection = sqlite3.connect(str(db_path))
    try:
        row = connection.execute(f"SELECT v FROM {table} LIMIT 1").fetchone()  # noqa: S608
        return str(row[0]) if row else ""
    finally:
        connection.close()


def _write_db(db_path: Path, value: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
        connection.execute("DELETE FROM t")
        connection.execute("INSERT INTO t (v) VALUES (?)", (value,))
        connection.commit()
    finally:
        connection.close()


def _archive_with_db(archive_path: Path, value: str, manifest: BackupManifest) -> None:
    import zipfile

    scratch = archive_path.parent / f"build-{value}"
    scratch.mkdir(parents=True, exist_ok=True)
    db_file = scratch / "data.db"
    _write_db(db_file, value)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(MANIFEST_MEMBER, manifest.to_json())
        archive.write(db_file, "data.db")


def _matching_manifest(settings: Settings, **overrides: object) -> BackupManifest:
    from snackbase.infrastructure.backup.manifest import (
        fingerprints_from_settings,
        load_alembic_heads,
        running_engine,
        snackbase_version,
    )

    prints = fingerprints_from_settings(settings)
    data = dict(
        format_version=1,
        created_at="2026-09-02T00:00:00+00:00",
        snackbase_version=snackbase_version(),
        backup_type="sqlite_physical",
        database_engine=running_engine(settings.database_url),
        alembic_heads=load_alembic_heads(),
        includes_files=False,
        storage_mode="local",
        encryption_key_fingerprint=prints["encryption_key_fingerprint"],
        secret_key_fingerprint=prints["secret_key_fingerprint"],
        token_secret_fingerprint=prints["token_secret_fingerprint"],
        table_row_counts={},
    )
    data.update(overrides)
    return BackupManifest(**data)  # type: ignore[arg-type]


class TestMarker:
    def test_write_and_read_marker_round_trip(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        marker = write_marker(
            settings,
            archive_name="x.zip",
            destination={"type": "local", "local_path": str(tmp_path / "backups")},
            requested_by="user-1",
            manifest_fingerprints={"encryption_key_fingerprint": "abc"},
        )
        assert marker["archive_name"] == "x.zip"
        stored = read_marker(settings)
        assert stored == marker

    def test_malformed_marker_renamed_and_boot_continues(
        self, tmp_path: Path
    ) -> None:
        settings = _make_settings(tmp_path)
        settings.database_url  # noqa: B018 - force path resolution base
        marker_file = tmp_path / "sb_data" / MARKER_FILENAME
        marker_file.parent.mkdir(parents=True)
        marker_file.write_text("{not json")

        assert execute_pending_restore(settings) is None
        assert not marker_file.exists()
        assert (tmp_path / "sb_data" / (MARKER_FILENAME + ".invalid")).exists()

    def test_absent_marker_returns_none(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        assert read_marker(settings) is None
        assert execute_pending_restore(settings) is None


class TestExecutePendingRestore:
    async def test_full_restore_replaces_database_and_preserves_old(
        self, tmp_path: Path
    ) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)

        # Live data, then a backup of it.
        _write_db(db_path, "before-backup")
        await create_backup(
            name="restore_me.zip", destination=destination, settings=settings
        )
        # Post-backup change that the restore must discard.
        _write_db(db_path, "after-backup")

        write_marker(
            settings,
            archive_name="restore_me.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="user-1",
            manifest_fingerprints={"encryption_key_fingerprint": "abc"},
        )

        result = execute_pending_restore(settings)

        assert result is not None
        assert result.status == "completed"
        assert result.archive_name == "restore_me.zip"
        assert _db_value(db_path) == "before-backup"

        # Old data preserved, marker gone, staging gone, outcome recorded.
        old_root = tmp_path / "sb_data" / RESTORE_OLD_DIRNAME
        preserved = list(old_root.iterdir())
        assert len(preserved) == 1
        assert _db_value(preserved[0] / "data.db") == "after-backup"
        assert read_marker(settings) is None
        assert not (tmp_path / "sb_data" / ".restore_tmp").exists()
        last = read_last_restore(settings)
        assert last is not None and last.status == "completed"

    async def test_restore_moves_files_tree(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        _write_db(db_path, "live")
        files_dir = tmp_path / "sb_data" / "files" / "acc-1"
        files_dir.mkdir(parents=True)
        (files_dir / "keep.txt").write_text("keep")

        await create_backup(
            name="with_files.zip",
            destination=destination,
            settings=settings,
            session_factory=None,
        )
        # Wipe the files tree after the backup; the restore brings it back.
        import shutil as shutil_mod

        shutil_mod.rmtree(tmp_path / "sb_data" / "files")
        write_marker(
            settings,
            archive_name="with_files.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        result = execute_pending_restore(settings)

        assert result is not None and result.status == "completed"
        restored_file = tmp_path / "sb_data" / "files" / "acc-1" / "keep.txt"
        assert restored_file.is_file()
        assert restored_file.read_text() == "keep"

    def test_wal_and_shm_do_not_survive(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        _write_db(db_path, "live")
        # Simulated WAL siblings from the previous database.
        (db_path.parent / "snackbase.db-wal").write_bytes(b"wal")
        (db_path.parent / "snackbase.db-shm").write_bytes(b"shm")
        _archive_with_db(
            backups_dir / "clean.zip",
            "restored",
            _matching_manifest(settings),
        )
        write_marker(
            settings,
            archive_name="clean.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        result = execute_pending_restore(settings)

        assert result is not None and result.status == "completed"
        assert not (db_path.parent / "snackbase.db-wal").exists()
        assert not (db_path.parent / "snackbase.db-shm").exists()
        assert _db_value(db_path) == "restored"

    def test_fingerprint_mismatch_at_boot_aborts_and_keeps_original(
        self, tmp_path: Path
    ) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        _write_db(db_path, "original")
        _archive_with_db(
            backups_dir / "foreign.zip",
            "foreign",
            _matching_manifest(
                settings, encryption_key_fingerprint=fingerprint("another-key")
            ),
        )
        write_marker(
            settings,
            archive_name="foreign.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        with pytest.raises(RestoreAbortedError):
            execute_pending_restore(settings)

        assert _db_value(db_path) == "original"
        assert read_marker(settings) is not None
        last = read_last_restore(settings)
        assert last is not None and last.status == "failed"
        assert last.error is not None

    def test_missing_archive_aborts(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        write_marker(
            settings,
            archive_name="absent.zip",
            destination={"type": "local", "local_path": str(tmp_path / "backups")},
            requested_by="system",
            manifest_fingerprints={},
        )

        with pytest.raises(RestoreAbortedError):
            execute_pending_restore(settings)

    def test_member_path_escape_rejected_before_extraction(
        self, tmp_path: Path
    ) -> None:
        import zipfile

        settings = _make_settings(tmp_path)
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir(parents=True)
        evil = backups_dir / "evil.zip"
        with zipfile.ZipFile(evil, "w") as archive:
            archive.writestr(MANIFEST_MEMBER, _matching_manifest(settings).to_json())
            archive.writestr("data.db", b"db")
            archive.writestr("../evil.txt", b"payload")
        write_marker(
            settings,
            archive_name="evil.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        with pytest.raises(RestoreAbortedError):
            execute_pending_restore(settings)

        assert not (tmp_path / "evil.txt").exists()
        assert not (tmp_path / "sb_data" / "evil.txt").exists()

    def test_interrupted_attempt_rolls_back_then_restores(
        self, tmp_path: Path
    ) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        _write_db(db_path, "current")
        _archive_with_db(
            backups_dir / "target.zip", "target", _matching_manifest(settings)
        )
        # Simulate a crash mid-restore: data preserved but marker still present.
        old_dir = tmp_path / "sb_data" / RESTORE_OLD_DIRNAME / "20260901T000000"
        old_dir.mkdir(parents=True)
        _write_db(old_dir / "data.db", "preserved-pre-crash")
        write_marker(
            settings,
            archive_name="target.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        result = execute_pending_restore(settings)

        assert result is not None and result.status == "completed"
        # The interrupted attempt's data was authoritative first, then the
        # target archive replaced it.
        assert _db_value(db_path) == "target"

    def test_no_database_connection_before_swap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No SQLAlchemy engine may be created during the swap."""
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        _write_db(db_path, "live")
        _archive_with_db(
            backups_dir / "ok.zip", "ok", _matching_manifest(settings)
        )
        write_marker(
            settings,
            archive_name="ok.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        import snackbase.infrastructure.persistence.database as db_module

        def fail_engine(*args: object, **kwargs: object) -> None:
            raise AssertionError("Database engine created during restore swap")

        monkeypatch.setattr(db_module, "create_async_engine", fail_engine)

        result = execute_pending_restore(settings)
        assert result is not None and result.status == "completed"


class TestOldRetention:
    def test_old_directory_removed_and_recent_kept(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path, restore_retain_old_data_hours=24)
        old_root = tmp_path / "sb_data" / RESTORE_OLD_DIRNAME
        ancient = old_root / "20260801T000000"
        recent = old_root / "20260902T000000"
        ancient.mkdir(parents=True)
        recent.mkdir(parents=True)
        ancient_stamp = time.time() - 25 * 3600
        os.utime(ancient, (ancient_stamp, ancient_stamp))

        assert execute_pending_restore(settings) is None

        assert not ancient.exists()
        assert recent.exists()

    def test_recent_directory_survives(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path, restore_retain_old_data_hours=24)
        old_root = tmp_path / "sb_data" / RESTORE_OLD_DIRNAME
        fresh = old_root / "20260902T010000"
        fresh.mkdir(parents=True)
        fresh_stamp = time.time() - 1 * 3600
        os.utime(fresh, (fresh_stamp, fresh_stamp))

        execute_pending_restore(settings)

        assert fresh.exists()


class TestAuditPendingFlag:
    def test_flag_written_on_completion(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        db_path = tmp_path / "sb_data" / "snackbase.db"
        backups_dir = tmp_path / "backups"
        _write_db(db_path, "live")
        _archive_with_db(backups_dir / "ok.zip", "ok", _matching_manifest(settings))
        write_marker(
            settings,
            archive_name="ok.zip",
            destination={"type": "local", "local_path": str(backups_dir)},
            requested_by="system",
            manifest_fingerprints={},
        )

        execute_pending_restore(settings)

        flag = tmp_path / "sb_data" / AUDIT_PENDING_FILENAME
        assert flag.exists()
        payload = json.loads(flag.read_text())
        assert payload["event"] == "backup.restore.completed"
        assert payload["archive_name"] == "ok.zip"
        popped = pop_audit_pending(settings)
        assert popped is not None and popped["event"] == "backup.restore.completed"
        assert pop_audit_pending(settings) is None


class TestRestoreStatus:
    def test_read_last_restore_absent(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        assert read_last_restore(settings) is None

    def test_read_last_restore_present(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        data_dir = tmp_path / "sb_data"
        data_dir.mkdir(parents=True)
        (data_dir / LAST_RESTORE_FILENAME).write_text(
            json.dumps(
                {
                    "archive_name": "x.zip",
                    "status": "failed",
                    "completed_at": "2026-09-02T00:00:00+00:00",
                    "error": "boom",
                }
            )
        )

        result = read_last_restore(settings)

        assert result is not None
        assert result.status == "failed"
        assert result.error == "boom"
