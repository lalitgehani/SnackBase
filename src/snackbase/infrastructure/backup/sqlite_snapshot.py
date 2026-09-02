"""Consistent SQLite snapshots via ``VACUUM INTO``.

A raw file copy of a live WAL-mode SQLite database can capture a torn
snapshot. ``VACUUM INTO`` writes a transactionally consistent copy while
holding only a brief lock — the same mechanism PocketBase uses for its
backups. ``VACUUM`` cannot run inside a transaction, so the connection runs
with ``isolation_level="AUTOCOMMIT"``.
"""

import sqlite3
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.infrastructure.backup.destinations import UnsupportedEngineError

#: Three slashes: everything after them is the file path itself, which for
#: absolute locations carries its own leading slash (``sqlite:////abs/x.db``).
SQLITE_URL_PREFIXES = ("sqlite+aiosqlite:///", "sqlite:///")


def sqlite_file_path(database_url: str) -> Path:
    """Resolve the SQLite database file path from a database URL.

    Raises:
        UnsupportedEngineError: When the URL does not point at SQLite.
    """
    for prefix in SQLITE_URL_PREFIXES:
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix) :]
            return Path(raw_path)
    raise UnsupportedEngineError(
        "SQLite backup requires a sqlite database URL; "
        "this instance is configured with a different engine"
    )


async def snapshot_sqlite(engine: AsyncEngine, dest_path: Path) -> None:
    """Write a transactionally consistent copy of the database to ``dest_path``.

    The output is a standalone SQLite file: openable by sqlite3, passing
    ``PRAGMA integrity_check``, and independent of the live WAL. After the
    copy the live database gets ``PRAGMA wal_checkpoint(TRUNCATE)`` so WAL
    growth from the vacuum does not accumulate; errors from that pragma are
    ignored — they must not fail an otherwise complete backup.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(
            text("VACUUM INTO :path"),
            {"path": str(dest_path.resolve())},
        )
        try:
            await connection.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        except Exception:  # noqa: BLE001 - the checkpoint is best-effort
            pass


def snapshot_sqlite_sync(database_path: Path, dest_path: Path) -> None:
    """Synchronous variant used by CLI and pre-boot paths.

    Opens its own sqlite3 connection (AUTOCOMMIT by default outside
    ``BEGIN``) and runs the same ``VACUUM INTO``.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("VACUUM INTO ?", (str(dest_path.resolve()),))
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
    finally:
        connection.close()
