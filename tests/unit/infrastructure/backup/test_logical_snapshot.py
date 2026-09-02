"""Unit tests for the logical snapshot reader (F5.1)."""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from snackbase.infrastructure.backup.logical_snapshot import (
    EXCLUDED_TABLES,
    decode_value,
    encode_value,
    iter_tables,
)


class TestValueEncoding:
    def test_datetime_encodes_iso8601(self) -> None:
        moment = datetime(2026, 9, 2, 3, 4, 5, tzinfo=UTC)
        assert encode_value(moment) == "2026-09-02T03:04:05+00:00"

    def test_date_encodes_iso8601(self) -> None:
        assert encode_value(datetime(2026, 9, 2).date()) == "2026-09-02"

    def test_bytes_encode_base64_wrapped_and_round_trip(self) -> None:
        encoded = encode_value(b"\x00\xffbinary")

        assert encoded == {"__b64__": "AP9iaW5hcnk="}
        assert decode_value(encoded) == b"\x00\xffbinary"

    def test_decimal_encodes_as_string(self) -> None:
        assert encode_value(Decimal("12.34")) == "12.34"

    def test_none_stays_null(self) -> None:
        assert encode_value(None) is None

    def test_primitives_pass_through(self) -> None:
        assert encode_value("text") == "text"
        assert encode_value(7) == 7
        assert encode_value(True) is True


class TestExcludedTables:
    def test_excluded_list_content(self) -> None:
        assert EXCLUDED_TABLES == frozenset(
            {
                "alembic_version",
                "token_blacklist",
                "refresh_tokens",
                "password_resets",
                "email_verifications",
            }
        )


class TestIterTablesSqlite:
    async def test_reads_snapshot_copy_including_dynamic_tables(self, tmp_path: Path) -> None:
        """Core and dynamic tables export; ephemeral tables do not."""
        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        connection = sqlite3.connect(str(db_path))
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO users (name) VALUES ('alice')")
        # A dynamic collection table plus its catalog row.
        connection.execute("CREATE TABLE col_notes (id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO col_notes (body) VALUES ('hello')")
        connection.execute("CREATE TABLE collections (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO collections (name) VALUES ('notes')")
        # Ephemeral tables exist in the snapshot but must be excluded.
        connection.execute("CREATE TABLE token_blacklist (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
        connection.commit()
        connection.close()

        exported: dict[str, list[dict]] = {}
        async for table_name, rows in iter_tables(engine):
            exported[table_name] = [row async for row in rows]
        await engine.dispose()

        assert exported["users"] == [{"id": 1, "name": "alice"}]
        assert exported["col_notes"] == [{"id": 1, "body": "hello"}]
        assert "collections" in exported
        assert "token_blacklist" not in exported
        assert "alembic_version" not in exported

    async def test_reads_from_vacuum_copy_not_live_database(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The live database file is only touched via VACUUM INTO."""
        import snackbase.infrastructure.backup.logical_snapshot as module

        db_path = tmp_path / "live.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        connection = sqlite3.connect(str(db_path))
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()

        snapshot_calls: list[Path] = []
        real_snapshot = module.snapshot_sqlite

        async def spy_snapshot(engine_: object, dest: Path) -> None:
            snapshot_calls.append(dest)
            await real_snapshot(engine_, dest)  # type: ignore[arg-type]

        monkeypatch.setattr(module, "snapshot_sqlite", spy_snapshot)
        explicit = tmp_path / "explicit.db"
        async for _table, _rows in iter_tables(engine, snapshot_path=explicit):
            pass
        await engine.dispose()

        assert snapshot_calls == [explicit]
        assert explicit.exists()

    async def test_empty_database_exports_nothing(self, tmp_path: Path) -> None:
        db_path = tmp_path / "live.db"
        sqlite3.connect(str(db_path)).close()
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

        exported = [table async for table, _rows in iter_tables(engine)]
        await engine.dispose()

        assert exported == []
