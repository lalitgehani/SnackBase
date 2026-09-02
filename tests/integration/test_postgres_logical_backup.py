"""PostgreSQL integration tests for logical backups (F5.1-F5.3).

These run only when ``SNACKBASE_TEST_POSTGRES_URL`` is configured, e.g.::

    SNACKBASE_TEST_POSTGRES_URL=postgresql+asyncpg://sb:sb@localhost:5432/sb_test
"""

import json
import os
from pathlib import Path

import pytest

from snackbase.infrastructure.backup.destinations import LocalBackupDestination
from snackbase.infrastructure.backup.service import (
    classify_archive,
    create_backup,
    resolve_backup_type,
)

POSTGRES_URL = os.environ.get("SNACKBASE_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="SNACKBASE_TEST_POSTGRES_URL is not configured",
)


def _make_settings(tmp_path: Path):
    from snackbase.core.config import Settings

    return Settings(
        database_url=POSTGRES_URL,
        storage_path=str(tmp_path / "files"),
        _env_file=None,
    )


async def _seed(engine, table: str = "pg_roundtrip") -> None:
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "id INTEGER PRIMARY KEY, "
                "payload JSONB, "
                "content BYTEA, "
                "seen_at TIMESTAMPTZ)"
            )
        )
        await conn.execute(
            text(
                f"INSERT INTO {table} (id, payload, content, seen_at) "
                "VALUES (1, '{\"a\": [1, 2], \"b\": \"x\"}'::jsonb, "
                "'\\x00ff'::bytea, '2026-09-02T03:04:05+00:00'::timestamptz) "
                "ON CONFLICT (id) DO NOTHING"
            )
        )


@pytest.mark.asyncio
async def test_logical_backup_round_trips_jsonb(tmp_path: Path) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = _make_settings(tmp_path)
    engine = create_async_engine(POSTGRES_URL)
    await _seed(engine)

    backups_dir = tmp_path / "backups"
    destination = LocalBackupDestination(backups_dir)
    await create_backup(
        name="pg_logical.zip",
        destination=destination,
        settings=settings,
        backup_type="logical",
    )
    await engine.dispose()

    import zipfile

    with zipfile.ZipFile(backups_dir / "pg_logical.zip") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        line = archive.read("tables/pg_roundtrip.jsonl").decode().splitlines()[0]

    assert manifest["backup_type"] == "logical"
    assert manifest["database_engine"] == "postgresql"
    assert set(manifest["excluded_tables"]) >= {
        "alembic_version",
        "token_blacklist",
        "refresh_tokens",
        "password_resets",
        "email_verifications",
    }

    row = json.loads(line)
    # JSONB round-trips to an equal structure.
    assert row["payload"] == {"a": [1, 2], "b": "x"}
    # Bytea round-trips through the base64 wrapper.
    from snackbase.infrastructure.backup.logical_snapshot import decode_value

    assert decode_value(row["content"]) == b"\x00\xff"
    assert row["seen_at"] == "2026-09-02T03:04:05+00:00"

    archive_type, restorable = await classify_archive(destination, "pg_logical.zip")
    assert (archive_type, restorable) == ("logical", False)


@pytest.mark.asyncio
async def test_concurrent_inserts_do_not_tear_export(tmp_path: Path) -> None:
    """Rows inserted mid-export never produce torn table counts."""
    import asyncio

    from sqlalchemy import func, select, text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = _make_settings(tmp_path)
    engine = create_async_engine(POSTGRES_URL)
    await _seed(engine, "pg_torn")

    async def insert_more() -> None:
        for index in range(50):
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        f"INSERT INTO pg_torn (id, payload) VALUES ({100 + index}, '{index}')"
                        " ON CONFLICT (id) DO NOTHING"
                    )
                )
            await asyncio.sleep(0)

    backups_dir = tmp_path / "backups"
    destination = LocalBackupDestination(backups_dir)
    insert_task = asyncio.create_task(insert_more())
    await create_backup(
        name="pg_torn.zip",
        destination=destination,
        settings=settings,
        backup_type="logical",
    )
    await insert_task
    async with engine.begin() as conn:
        total = await conn.scalar(select(func.count()).select_from(text("pg_torn")))
    await engine.dispose()

    import zipfile

    with zipfile.ZipFile(backups_dir / "pg_torn.zip") as archive:
        lines = archive.read("tables/pg_torn.jsonl").decode().splitlines()
    assert len(lines) == int(total)
    assert all(json.loads(line) for line in lines)


def test_postgres_routes_to_logical() -> None:
    assert resolve_backup_type(None, POSTGRES_URL) == "logical"
    with pytest.raises(ValueError, match="sqlite_physical"):
        resolve_backup_type("sqlite_physical", POSTGRES_URL)
