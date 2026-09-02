"""Unit tests for SQLite snapshots (F2.1)."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from snackbase.infrastructure.backup.destinations import UnsupportedEngineError
from snackbase.infrastructure.backup.sqlite_snapshot import (
    snapshot_sqlite,
    sqlite_file_path,
)


def _integrity_check(path: Path) -> str:
    connection = sqlite3.connect(str(path))
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "unknown"
    finally:
        connection.close()


class TestSqliteFilePath:
    def test_resolves_aiosqlite_url(self) -> None:
        assert sqlite_file_path("sqlite+aiosqlite:///./sb_data/snackbase.db") == Path(
            "./sb_data/snackbase.db"
        )

    def test_resolves_plain_sqlite_url(self) -> None:
        assert sqlite_file_path("sqlite:////abs/path.db") == Path("/abs/path.db")

    def test_postgresql_url_raises_unsupported(self) -> None:
        with pytest.raises(UnsupportedEngineError):
            sqlite_file_path("postgresql+asyncpg://u:p@localhost/db")


class TestSnapshotSqlite:
    async def test_snapshot_passes_integrity_check(self, tmp_path: Path) -> None:
        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
            await conn.execute(text("INSERT INTO t (v) VALUES ('a'), ('b')"))
        snapshot_path = tmp_path / "snap.db"

        try:
            await snapshot_sqlite(engine, snapshot_path)
        finally:
            await engine.dispose()

        assert snapshot_path.exists()
        assert _integrity_check(snapshot_path) == "ok"
        connection = sqlite3.connect(str(snapshot_path))
        try:
            count = connection.execute("SELECT COUNT(*) FROM t").fetchone()
        finally:
            connection.close()
        assert count is not None and count[0] == 2

    async def test_snapshot_is_independent_of_wal(self, tmp_path: Path) -> None:
        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
            await conn.execute(text("INSERT INTO t DEFAULT VALUES"))
        snapshot_path = tmp_path / "snap.db"

        try:
            await snapshot_sqlite(engine, snapshot_path)
        finally:
            await engine.dispose()

        # The snapshot is a standalone file: openable with no WAL siblings.
        connection = sqlite3.connect(str(snapshot_path))
        try:
            count = connection.execute("SELECT COUNT(*) FROM t").fetchone()
        finally:
            connection.close()
        assert count is not None and count[0] == 1

    async def test_wal_checkpoint_truncates_wal(self, tmp_path: Path) -> None:
        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
            await conn.execute(text("INSERT INTO t DEFAULT VALUES"))
        snapshot_path = tmp_path / "snap.db"

        try:
            await snapshot_sqlite(engine, snapshot_path)
            # After the checkpoint the WAL is truncated (or removed); it must
            # not have grown without bound.
            wal = tmp_path / "live.db-wal"
            if wal.exists():
                assert wal.stat().st_size == 0
        finally:
            await engine.dispose()

    async def test_snapshot_overwrites_existing_output(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
        snapshot_path = tmp_path / "snap.db"
        snapshot_path.write_bytes(b"stale")

        try:
            await snapshot_sqlite(engine, snapshot_path)
        finally:
            await engine.dispose()

        assert _integrity_check(snapshot_path) == "ok"
