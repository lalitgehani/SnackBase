"""Integration tests for the backup CLI (F2.5)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from snackbase.cli import cli
from snackbase.infrastructure.persistence.database import Base
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel


@pytest.fixture
def cli_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """A migrated scratch database plus a backup_settings row pointing at tmp."""
    db_path = tmp_path / "cli_instance" / "snackbase.db"
    db_path.parent.mkdir(parents=True)
    backup_dir = tmp_path / "cli_backups"

    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    with Session(sync_engine) as session:
        session.add(
            ConfigurationModel(
                id="cli-backup-cfg",
                account_id="00000000-0000-0000-0000-000000000000",
                category="backup_settings",
                provider_name="backup",
                display_name="Backup Settings",
                config={
                    "destination": "local",
                    "local_path": str(backup_dir),
                },
                enabled=True,
                is_builtin=True,
                is_system=True,
            )
        )
        session.commit()
    sync_engine.dispose()

    monkeypatch.setenv("SNACKBASE_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from snackbase.core.config import get_settings
    from snackbase.infrastructure.persistence import database as database_module

    get_settings.cache_clear()
    # Drop the process-wide manager singleton so the CLI builds one bound to
    # this test's settings rather than a previous test's disposed engine.
    database_module._db_manager = None
    yield backup_dir, db_path
    get_settings.cache_clear()


def _audit_events(db_path: Path) -> list[AuditLogModel]:
    sync_engine = create_engine(f"sqlite:///{db_path}")
    try:
        with Session(sync_engine) as session:
            return list(
                session.scalars(
                    select(AuditLogModel).where(AuditLogModel.table_name == "backup")
                )
            )
    finally:
        sync_engine.dispose()


def _jobs_count(db_path: Path) -> int:
    sync_engine = create_engine(f"sqlite:///{db_path}")
    try:
        with Session(sync_engine) as session:
            from snackbase.infrastructure.persistence.models.job import JobModel

            return len(list(session.scalars(select(JobModel))))
    finally:
        sync_engine.dispose()


class TestBackupCreate:
    def test_create_produces_archive_and_audit_entries(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        backup_dir, db_path = cli_environment
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "create", "--name", "cli_backup.zip"])

        assert result.exit_code == 0, result.output
        archive = backup_dir / "cli_backup.zip"
        assert archive.exists()
        assert archive.stat().st_size > 0
        assert "cli_backup.zip" in result.output

        events = sorted(entry.new_value or "" for entry in _audit_events(db_path))
        assert events == ["backup.create.completed", "backup.create.started"]

        completed = [
            entry
            for entry in _audit_events(db_path)
            if entry.new_value == "backup.create.completed"
        ]
        assert len(completed) == 1
        metadata = completed[0].extra_metadata or {}
        assert metadata.get("size") == archive.stat().st_size
        # CLI operations act as the system actor.
        assert metadata.get("actor") == "system"

    def test_create_without_name_autogenerates(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        import re

        backup_dir, _db_path = cli_environment
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "create"])

        assert result.exit_code == 0, result.output
        assert re.search(r"snackbase_backup_\d{14}\.zip", result.output)
        assert any(backup_dir.glob("snackbase_backup_*.zip"))

    def test_create_while_in_flight_exits_non_zero(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        import os

        from snackbase.infrastructure.backup.lock import LOCK_FILENAME

        backup_dir, _db_path = cli_environment
        backup_dir.mkdir(parents=True)
        (backup_dir / LOCK_FILENAME).write_text(
            json.dumps(
                {
                    "operation": "backup",
                    "name": "busy.zip",
                    "pid": os.getpid(),
                    "started_at": "2026-09-02T00:00:00",
                }
            )
        )
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "create", "--name", "x.zip"])

        assert result.exit_code != 0
        assert "in progress" in result.output

    def test_create_writes_no_job_rows(self, cli_environment: tuple[Path, Path]) -> None:
        backup_dir, db_path = cli_environment
        runner = CliRunner()

        before = _jobs_count(db_path)
        result = runner.invoke(cli, ["backup", "create", "--name", "nojobs.zip"])
        after = _jobs_count(db_path)

        assert result.exit_code == 0, result.output
        assert (backup_dir / "nojobs.zip").exists()
        assert before == 0
        assert after == 0


class TestBackupList:
    def test_lists_entries_with_size_and_auto_marker(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        backup_dir, _db_path = cli_environment
        backup_dir.mkdir(parents=True)
        (backup_dir / "@auto_one.zip").write_bytes(b"x" * 2048)
        (backup_dir / "manual_two.zip").write_bytes(b"y" * 1024)
        (backup_dir / "notes.txt").write_bytes(b"not an archive")
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 0, result.output
        assert "@auto_one.zip" in result.output
        assert "manual_two.zip" in result.output
        assert "notes.txt" not in result.output
        assert "2.0KB" in result.output
        assert "auto" in result.output
        assert "manual" in result.output

    def test_empty_destination(self, cli_environment: tuple[Path, Path]) -> None:
        _backup_dir, _db_path = cli_environment
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 0, result.output
        assert "No backups found." in result.output


class TestBackupDelete:
    def test_delete_prompts_without_yes(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        backup_dir, db_path = cli_environment
        backup_dir.mkdir(parents=True)
        archive = backup_dir / "goner.zip"
        archive.write_bytes(b"payload")
        runner = CliRunner()

        declined = runner.invoke(
            cli, ["backup", "delete", "goner.zip"], input="n\n"
        )
        assert declined.exit_code != 0
        assert archive.exists()

        confirmed = runner.invoke(cli, ["backup", "delete", "goner.zip"], input="y\n")
        assert confirmed.exit_code == 0, confirmed.output
        assert not archive.exists()
        events = [entry.new_value for entry in _audit_events(db_path)]
        assert "backup.delete" in events

    def test_delete_with_yes_flag_skips_prompt(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        backup_dir, _db_path = cli_environment
        backup_dir.mkdir(parents=True)
        archive = backup_dir / "goner.zip"
        archive.write_bytes(b"payload")
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "delete", "goner.zip", "--yes"])

        assert result.exit_code == 0, result.output
        assert "Delete backup" not in result.output
        assert not archive.exists()

    def test_delete_absent_archive_exits_non_zero(
        self, cli_environment: tuple[Path, Path]
    ) -> None:
        _backup_dir, _db_path = cli_environment
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "delete", "absent.zip", "--yes"])

        assert result.exit_code != 0


class TestBackupRestore:
    @pytest.fixture
    def restore_setup(
        self, cli_environment: tuple[Path, Path]
    ) -> tuple[Path, Path, Path]:
        """An archive at the destination plus its paths for assertions."""
        import zipfile

        from snackbase.core.config import get_settings
        from snackbase.infrastructure.backup.manifest import (
            BackupManifest,
            fingerprints_from_settings,
            load_alembic_heads,
            running_engine,
            snackbase_version,
        )

        backup_dir, db_path = cli_environment
        backup_dir.mkdir(parents=True, exist_ok=True)
        settings = get_settings()
        prints = fingerprints_from_settings(settings)
        manifest = BackupManifest(
            format_version=1,
            created_at="2026-09-02T02:00:00+00:00",
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
        archive = backup_dir / "cli_restore.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("manifest.json", manifest.to_json())
            zf.writestr("data.db", b"SQLite format 3\x00")
        marker_path = db_path.parent / ".restore-pending.json"
        return backup_dir, db_path, marker_path

    def test_restore_yes_writes_marker_and_prints_summary(
        self, restore_setup: tuple[Path, Path, Path]
    ) -> None:
        backup_dir, _db_path, marker_path = restore_setup
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "restore", "cli_restore.zip", "--yes"])

        assert result.exit_code == 0, result.output
        assert "cli_restore.zip" in result.output
        assert "2026-09-02T02:00:00+00:00" in result.output
        assert "next start" in result.output
        assert "unless-stopped" in result.output
        assert marker_path.exists()
        marker = json.loads(marker_path.read_text())
        assert marker["archive_name"] == "cli_restore.zip"
        assert marker["requested_by"] == "system"
        assert marker["destination"]["type"] == "local"

    def test_restore_prompts_without_yes(
        self, restore_setup: tuple[Path, Path, Path]
    ) -> None:
        _backup_dir, _db_path, marker_path = restore_setup
        runner = CliRunner()

        declined = runner.invoke(
            cli, ["backup", "restore", "cli_restore.zip"], input="n\n"
        )
        assert declined.exit_code != 0
        assert not marker_path.exists()

        confirmed = runner.invoke(
            cli, ["backup", "restore", "cli_restore.zip"], input="y\n"
        )
        assert confirmed.exit_code == 0, confirmed.output
        assert marker_path.exists()

    def test_restore_incompatible_archive_exits_non_zero(
        self, restore_setup: tuple[Path, Path, Path]
    ) -> None:
        import zipfile

        from snackbase.core.config import get_settings
        from snackbase.infrastructure.backup.manifest import (
            BackupManifest,
            fingerprint,
        )

        backup_dir, _db_path, marker_path = restore_setup
        settings = get_settings()
        manifest = BackupManifest(
            format_version=1,
            created_at="2026-09-02T02:00:00+00:00",
            snackbase_version="0.11.0",
            backup_type="sqlite_physical",
            database_engine="sqlite",
            alembic_heads=[],
            includes_files=False,
            storage_mode="local",
            encryption_key_fingerprint=fingerprint("a-different-key"),
            secret_key_fingerprint=prints_key(settings.secret_key),
            token_secret_fingerprint=prints_key(settings.token_secret),
            table_row_counts={},
        )
        archive = backup_dir / "foreign.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("manifest.json", manifest.to_json())
            zf.writestr("data.db", b"x")
        runner = CliRunner()

        result = runner.invoke(cli, ["backup", "restore", "foreign.zip", "--yes"])

        assert result.exit_code != 0
        assert "BLOCKING" in result.output
        assert not marker_path.exists()

    def test_restore_warning_archive_requires_force(
        self, restore_setup: tuple[Path, Path, Path]
    ) -> None:
        import zipfile

        from snackbase.core.config import get_settings
        from snackbase.infrastructure.backup.manifest import (
            BackupManifest,
            fingerprint,
            fingerprints_from_settings,
        )

        backup_dir, _db_path, marker_path = restore_setup
        settings = get_settings()
        prints = fingerprints_from_settings(settings)
        manifest = BackupManifest(
            format_version=1,
            created_at="2026-09-02T02:00:00+00:00",
            snackbase_version="0.11.0",
            backup_type="sqlite_physical",
            database_engine="sqlite",
            alembic_heads=[],
            includes_files=False,
            storage_mode="local",
            encryption_key_fingerprint=prints["encryption_key_fingerprint"],
            secret_key_fingerprint=fingerprint("rotated-key"),
            token_secret_fingerprint=prints["token_secret_fingerprint"],
            table_row_counts={},
        )
        archive = backup_dir / "warned.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("manifest.json", manifest.to_json())
            zf.writestr("data.db", b"x")
        runner = CliRunner()

        without_force = runner.invoke(
            cli, ["backup", "restore", "warned.zip", "--yes"]
        )
        assert without_force.exit_code != 0
        assert "WARNING" in without_force.output
        assert not marker_path.exists()

        with_force = runner.invoke(
            cli, ["backup", "restore", "warned.zip", "--yes", "--force"]
        )
        assert with_force.exit_code == 0, with_force.output
        assert marker_path.exists()


def prints_key(secret: str) -> str:
    from snackbase.infrastructure.backup.manifest import fingerprint

    return fingerprint(secret)
