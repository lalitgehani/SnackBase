"""Unit tests for the backup service (F2.1)."""

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from snackbase.core.config import Settings
from snackbase.infrastructure.backup.archive import member_names
from snackbase.infrastructure.backup.destinations import (
    BackupExistsError,
    LocalBackupDestination,
    UnsupportedEngineError,
)
from snackbase.infrastructure.backup.service import (
    backup_working_dir,
    collect_row_counts,
    create_backup,
    generate_backup_name,
    resolve_storage_mode,
    staging_dir,
)
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'live.db'}",
        storage_path=str(tmp_path / "files"),
        _env_file=None,
        **overrides,  # type: ignore[arg-type]
    )


async def _seed_database(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'live.db'}")
    async with engine.begin() as conn:
        await conn.execute(_text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        await conn.execute(_text("INSERT INTO users DEFAULT VALUES"))
        await conn.execute(_text("CREATE TABLE accounts (id INTEGER PRIMARY KEY)"))
        await conn.execute(_text("INSERT INTO accounts DEFAULT VALUES"))
    await engine.dispose()


def _text(query: str):
    from sqlalchemy import text

    return text(query)


class TestCollectRowCounts:
    def test_counts_match_snapshot_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "snap.db"
        connection = sqlite3.connect(str(db_path))
        try:
            connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            connection.execute("CREATE TABLE col_notes (id INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO users DEFAULT VALUES")
            connection.execute("INSERT INTO users DEFAULT VALUES")
            connection.execute("INSERT INTO col_notes DEFAULT VALUES")
            connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
            connection.commit()
        finally:
            connection.close()

        counts = collect_row_counts(db_path)

        assert counts == {"users": 2, "col_notes": 1}
        assert "alembic_version" not in counts

    def test_empty_database_yields_empty_counts(self, tmp_path: Path) -> None:
        db_path = tmp_path / "snap.db"
        sqlite3.connect(str(db_path)).close()

        assert collect_row_counts(db_path) == {}


class TestResolveStorageMode:
    async def test_no_configuration_means_local(self, db_session) -> None:
        assert await resolve_storage_mode(db_session) == "local"

    async def test_s3_configuration_detected(self, db_session) -> None:
        db_session.add(
            ConfigurationModel(
                id="cfg-s3-1",
                account_id="00000000-0000-0000-0000-000000000000",
                category="storage_providers",
                provider_name="s3",
                display_name="S3",
                config={"bucket": "b"},
                enabled=True,
                is_builtin=True,
                is_system=True,
            )
        )
        await db_session.commit()

        assert await resolve_storage_mode(db_session) == "s3"


class TestBackupWorkingDir:
    def test_local_destination_uses_its_own_directory(self, tmp_path: Path) -> None:
        destination = LocalBackupDestination(tmp_path / "backups")
        assert backup_working_dir(destination) == tmp_path / "backups"

    def test_remote_destination_uses_default_directory(self) -> None:
        from unittest.mock import MagicMock

        from snackbase.infrastructure.backup.destinations import BackupDestination

        remote = MagicMock(spec=BackupDestination)
        assert backup_working_dir(remote) == Path("./sb_data/backups")


class TestGenerateBackupName:
    def test_name_format(self) -> None:
        import re

        name = generate_backup_name()
        assert re.fullmatch(r"snackbase_backup_\d{14}\.zip", name)


class TestCreateBackup:
    async def test_creates_archive_with_manifest_data_and_files(
        self, tmp_path: Path
    ) -> None:
        await _seed_database(tmp_path)
        files_dir = tmp_path / "files" / "acc-1"
        files_dir.mkdir(parents=True)
        (files_dir / "hello.txt").write_text("hello")
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        settings = _make_settings(tmp_path)

        outcome = await create_backup(
            name="test.zip",
            destination=destination,
            settings=settings,
        )

        assert outcome.name == "test.zip"
        assert outcome.size > 0
        assert outcome.destination_type == "local"
        archive_path = backups_dir / "test.zip"
        assert archive_path.exists()
        names = member_names(archive_path)
        assert "manifest.json" in names
        assert "data.db" in names
        assert "files/acc-1/hello.txt" in names

        with zipfile.ZipFile(archive_path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            snapshot_bytes = archive.read("data.db")
        assert manifest["backup_type"] == "sqlite_physical"
        assert manifest["database_engine"] == "sqlite"
        assert manifest["includes_files"] is True
        assert manifest["storage_mode"] == "local"
        assert manifest["table_row_counts"]["users"] == 1

        # The snapshot inside the archive is a valid SQLite database.
        live_db = sqlite3.connect(str(tmp_path / "live.db"))
        snap_tmp = tmp_path / "from_archive.db"
        snap_tmp.write_bytes(snapshot_bytes)
        snap = sqlite3.connect(str(snap_tmp))
        try:
            live_count = live_db.execute("SELECT COUNT(*) FROM users").fetchone()
            snap_count = snap.execute("SELECT COUNT(*) FROM users").fetchone()
        finally:
            live_db.close()
            snap.close()
        assert snap_count == live_count

    async def test_staging_files_removed_after_success(
        self, tmp_path: Path
    ) -> None:
        await _seed_database(tmp_path)
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        settings = _make_settings(tmp_path)

        await create_backup(name="test.zip", destination=destination, settings=settings)

        staging = staging_dir(backups_dir)
        assert list(staging.iterdir()) == []

    async def test_staging_files_removed_after_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Fail mid-build (after staging files exist): staging must be clean
        # and no archive may appear at the destination.
        import snackbase.infrastructure.backup.service as service_module

        await _seed_database(tmp_path)
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        settings = _make_settings(tmp_path)

        async def explode(engine: object, dest_path: Path) -> None:
            dest_path.write_bytes(b"partial")
            raise RuntimeError("snapshot exploded")

        monkeypatch.setattr(service_module, "snapshot_sqlite", explode)

        with pytest.raises(RuntimeError):
            await create_backup(
                name="test.zip", destination=destination, settings=settings
            )

        staging = staging_dir(backups_dir)
        assert list(staging.iterdir()) == []
        assert not (backups_dir / "test.zip").exists()

    async def test_duplicate_name_rejected(self, tmp_path: Path) -> None:
        await _seed_database(tmp_path)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        await create_backup(name="test.zip", destination=destination, settings=settings)
        with pytest.raises(BackupExistsError):
            await create_backup(
                name="test.zip", destination=destination, settings=settings
            )

    async def test_backup_directory_never_enters_archive(
        self, tmp_path: Path
    ) -> None:
        await _seed_database(tmp_path)
        # The backup directory sits inside storage_path — it must never be
        # archived, and neither may an archive already in it.
        storage_root = tmp_path / "files"
        backups_dir = storage_root / "backups"
        backups_dir.mkdir(parents=True)
        (backups_dir / "previous.zip").write_bytes(b"old archive")
        user_file = storage_root / "acc-1"
        user_file.mkdir(parents=True)
        (user_file / "note.txt").write_text("note")
        destination = LocalBackupDestination(backups_dir)
        settings = _make_settings(tmp_path)

        await create_backup(name="test.zip", destination=destination, settings=settings)

        names = member_names(backups_dir / "test.zip")
        assert "files/acc-1/note.txt" in names
        assert not any("previous.zip" in name for name in names)
        assert not any(".tmp" in name for name in names)

    async def test_s3_storage_mode_excludes_files(self, tmp_path: Path, db_session) -> None:
        await _seed_database(tmp_path)
        files_dir = tmp_path / "files" / "acc-1"
        files_dir.mkdir(parents=True)
        (files_dir / "hello.txt").write_text("hello")
        db_session.add(
            ConfigurationModel(
                id="cfg-s3-2",
                account_id="00000000-0000-0000-0000-000000000000",
                category="storage_providers",
                provider_name="s3",
                display_name="S3",
                config={"bucket": "b"},
                enabled=True,
                is_builtin=True,
                is_system=True,
            )
        )
        await db_session.commit()

        captured_session_factory = _CaptureSessionFactory(db_session)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        await create_backup(
            name="test.zip",
            destination=destination,
            settings=settings,
            session_factory=captured_session_factory,
        )

        names = member_names(tmp_path / "backups" / "test.zip")
        assert not any(name.startswith("files/") for name in names)
        with zipfile.ZipFile(tmp_path / "backups" / "test.zip") as archive:
            manifest = json.loads(archive.read("manifest.json"))
        assert manifest["includes_files"] is False
        assert manifest["storage_mode"] == "s3"

    async def test_postgresql_url_raises_unsupported_engine(
        self, tmp_path: Path
    ) -> None:
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        settings = Settings(
            database_url="postgresql+asyncpg://u:p@localhost/db",
            _env_file=None,
        )

        with pytest.raises(UnsupportedEngineError):
            await create_backup(
                name="test.zip", destination=destination, settings=settings
            )
        assert not (backups_dir / "test.zip").exists()

    async def test_concurrent_backup_rejected_by_lock(self, tmp_path: Path) -> None:
        import asyncio

        from snackbase.infrastructure.backup.lock import backup_lock

        await _seed_database(tmp_path)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        async def hold_lock() -> None:
            async with backup_lock("held.zip", "backup", tmp_path / "backups"):
                await asyncio.sleep(0.2)

        await asyncio.gather(
            hold_lock(),
            _expect_in_progress(destination, settings),
        )

    async def test_manifest_records_alembic_heads(self, tmp_path: Path) -> None:
        await _seed_database(tmp_path)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        await create_backup(name="test.zip", destination=destination, settings=settings)

        with zipfile.ZipFile(tmp_path / "backups" / "test.zip") as archive:
            manifest = json.loads(archive.read("manifest.json"))
        assert isinstance(manifest["alembic_heads"], list)


async def _expect_in_progress(
    destination: LocalBackupDestination, settings: Settings
) -> None:
    from snackbase.infrastructure.backup.destinations import BackupInProgressError

    with pytest.raises(BackupInProgressError):
        await create_backup(
            name="other.zip", destination=destination, settings=settings
        )


class _CaptureSessionFactory:
    """Wraps an existing session in a factory-shaped callable."""

    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self._session = session

    def __call__(self):  # type: ignore[no-untyped-def]
        return _NullContext(self._session)


class _NullContext:
    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self._session = session

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self._session

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class TestLogicalArchive:
    async def test_logical_archive_layout_and_manifest(self, tmp_path: Path) -> None:
        await _seed_database(tmp_path)
        backups_dir = tmp_path / "backups"
        destination = LocalBackupDestination(backups_dir)
        settings = _make_settings(tmp_path)

        outcome = await create_backup(
            name="logical.zip",
            destination=destination,
            settings=settings,
            backup_type="logical",
        )

        assert outcome.manifest.backup_type == "logical"
        assert outcome.manifest.database_engine == "sqlite"
        archive_path = backups_dir / "logical.zip"
        names = member_names(archive_path)
        assert "manifest.json" in names
        assert "data.db" not in names
        assert "tables/users.jsonl" in names
        assert "tables/accounts.jsonl" in names

        import json as json_module

        with zipfile.ZipFile(archive_path) as archive:
            manifest = json_module.loads(archive.read("manifest.json"))
            users_lines = archive.read("tables/users.jsonl").decode().splitlines()
        assert manifest["backup_type"] == "logical"
        assert manifest["table_row_counts"] == {"users": 1, "accounts": 1}
        for line in users_lines:
            assert json_module.loads(line) == {"id": 1}

    async def test_logical_archive_through_destination_and_lock(
        self, tmp_path: Path
    ) -> None:
        import asyncio

        from snackbase.infrastructure.backup.lock import backup_lock

        await _seed_database(tmp_path)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        async def hold_lock() -> None:
            async with backup_lock("held.zip", "backup", tmp_path / "backups"):
                await asyncio.sleep(0.15)

        async def expect_error() -> None:
            from snackbase.infrastructure.backup.destinations import (
                BackupInProgressError,
            )

            with pytest.raises(BackupInProgressError):
                await create_backup(
                    name="other.zip",
                    destination=destination,
                    settings=settings,
                    backup_type="logical",
                )

        await asyncio.gather(hold_lock(), expect_error())


class TestResolveBackupType:
    def test_sqlite_defaults_to_physical(self) -> None:
        from snackbase.infrastructure.backup.service import resolve_backup_type

        assert (
            resolve_backup_type(None, "sqlite+aiosqlite:///./x.db")
            == "sqlite_physical"
        )

    def test_postgresql_defaults_to_logical(self) -> None:
        from snackbase.infrastructure.backup.service import resolve_backup_type

        assert (
            resolve_backup_type(None, "postgresql+asyncpg://u:p@h/db") == "logical"
        )

    def test_sqlite_can_request_logical(self) -> None:
        from snackbase.infrastructure.backup.service import resolve_backup_type

        assert (
            resolve_backup_type("logical", "sqlite+aiosqlite:///./x.db") == "logical"
        )

    def test_postgresql_rejects_physical(self) -> None:
        from snackbase.infrastructure.backup.service import resolve_backup_type

        with pytest.raises(ValueError, match="sqlite_physical"):
            resolve_backup_type("sqlite_physical", "postgresql+asyncpg://u:p@h/db")

    def test_unknown_type_rejected(self) -> None:
        from snackbase.infrastructure.backup.service import resolve_backup_type

        with pytest.raises(ValueError, match="type"):
            resolve_backup_type("tar", "sqlite+aiosqlite:///./x.db")


class TestClassifyArchive:
    async def test_physical_and_logical_classified(self, tmp_path: Path) -> None:
        await _seed_database(tmp_path)
        destination = LocalBackupDestination(tmp_path / "backups")
        settings = _make_settings(tmp_path)

        await create_backup(
            name="p.zip", destination=destination, settings=settings
        )
        await create_backup(
            name="l.zip",
            destination=destination,
            settings=settings,
            backup_type="logical",
        )

        from snackbase.infrastructure.backup.service import classify_archive

        physical_type, physical_restorable = await classify_archive(
            destination, "p.zip"
        )
        logical_type, logical_restorable = await classify_archive(destination, "l.zip")

        assert (physical_type, physical_restorable) == ("sqlite_physical", True)
        assert (logical_type, logical_restorable) == ("logical", False)
