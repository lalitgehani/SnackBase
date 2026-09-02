"""Consistent logical snapshot reader for PostgreSQL and SQLite.

PostgreSQL has no application-callable equivalent of ``VACUUM INTO``, so
logical consistency comes from a single ``REPEATABLE READ READ ONLY``
transaction: every table is read from the same snapshot and an export taken
under write load is never torn across tables. On SQLite the same guarantee
comes from reading a ``VACUUM INTO`` copy instead of the live database.

The reader streams rows in batches so a multi-gigabyte table never
materialises in memory, and encodes values as JSON-compatible types.
"""

import asyncio
import base64
import sqlite3
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.core.logging import get_logger
from snackbase.infrastructure.backup.sqlite_snapshot import snapshot_sqlite

logger = get_logger(__name__)

#: Fetch size for server-side cursors and batch reads.
FETCH_SIZE = 1000

#: Tables whose contents are meaningless outside their instance. The list is
#: recorded in the manifest so a reader knows what is absent by design.
EXCLUDED_TABLES = frozenset(
    {
        "alembic_version",
        "token_blacklist",
        "refresh_tokens",
        "password_resets",
        "email_verifications",
    }
)

B64_WRAPPER = "__b64__"


def encode_value(value: Any) -> Any:
    """Encode a database value as a JSON-compatible type.

    ``datetime``/``date`` become ISO-8601 strings, ``bytes`` becomes
    ``{"__b64__": "..."}``, ``Decimal`` becomes a string, ``None`` stays
    null.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {B64_WRAPPER: base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, (dict, list)):
        return value
    return str(value)


def decode_value(value: Any) -> Any:
    """Inverse of :func:`encode_value` for round-trip verification."""
    if isinstance(value, dict) and B64_WRAPPER in value:
        return base64.b64decode(value[B64_WRAPPER])
    return value


async def _dynamic_collection_tables(
    run_query: Callable[[Any], Awaitable[Any]],
) -> list[str]:
    """Names of dynamic collection tables resolved from the collections table."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder

    try:
        result = await run_query(text("SELECT name FROM collections"))
        names = [row[0] for row in result]
    except Exception as exc:  # noqa: BLE001 - no collections table yet
        logger.debug("No dynamic collection tables resolved", error=str(exc))
        return []
    return [TableBuilder.generate_table_name(name) for name in names]


def _core_table_names() -> list[str]:
    """Table names known to the SQLAlchemy metadata."""
    from snackbase.infrastructure.persistence.database import Base

    return sorted(table.name for table in Base.metadata.sorted_tables)


async def _enumerate_tables(
    engine: AsyncEngine,
    run_query: Callable[[Any], Awaitable[Any]],
    existing_tables: set[str] | None = None,
) -> list[str]:
    """Union of core and dynamic tables, excluding the ephemeral set."""
    core = _core_table_names()
    dynamic = await _dynamic_collection_tables(run_query)
    union: list[str] = []
    seen: set[str] = set()
    for name in [*core, *dynamic]:
        if name in seen or name in EXCLUDED_TABLES:
            continue
        if existing_tables is not None and name not in existing_tables:
            continue
        seen.add(name)
        union.append(name)
    return union


async def iter_tables(
    engine: AsyncEngine,
    *,
    snapshot_path: Path | None = None,
) -> AsyncIterator[tuple[str, AsyncIterator[dict[str, Any]]]]:
    """Yield ``(table_name, row_iterator)`` pairs from one consistent snapshot.

    On PostgreSQL every table is read inside a single ``REPEATABLE READ READ
    ONLY`` transaction via a server-side cursor per table. On SQLite the
    snapshot is taken with ``VACUUM INTO`` (to ``snapshot_path`` when given,
    else a temporary file) and read from that copy, keeping a single code
    path for archive writing.

    Rows are dictionaries with JSON-compatible values, streamed in batches
    of :data:`FETCH_SIZE` so large tables never materialise in memory.
    """
    if engine.dialect.name == "sqlite":
        async for item in _iter_tables_sqlite(engine, snapshot_path):
            yield item
        return

    # PostgreSQL: one connection, one consistent read-only transaction for
    # the entire export.
    async with engine.connect() as connection:
        await connection.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )

        async def run_query(query: Any) -> Any:
            return await connection.execute(query)

        existing = await _existing_postgres_tables(connection)
        tables = await _enumerate_tables(engine, run_query, existing_tables=existing)

        for table_name in tables:
            result = await connection.stream(
                text(f'SELECT * FROM "{table_name}"')  # noqa: S608
            )

            async def row_stream(
                result: Any = result,
                table_name: str = table_name,
            ) -> AsyncIterator[dict[str, Any]]:
                columns = list(result.keys())
                async for batch in result.mappings().partitions(FETCH_SIZE):
                    for row in batch:
                        yield {c: encode_value(row[c]) for c in columns}
                logger.debug("Table exported", table=table_name)

            yield table_name, row_stream()


async def _existing_postgres_tables(connection: Any) -> set[str]:
    result = await connection.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    return {row[0] for row in result}


async def _iter_tables_sqlite(
    engine: AsyncEngine,
    snapshot_path: Path | None,
) -> AsyncIterator[tuple[str, AsyncIterator[dict[str, Any]]]]:
    """Read tables from a VACUUM INTO copy of the live SQLite database."""
    import tempfile

    owned_temp = snapshot_path is None
    if owned_temp:
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        snapshot = Path(handle.name)
        handle.close()
    else:
        assert snapshot_path is not None
        snapshot = Path(snapshot_path)

    try:
        await snapshot_sqlite(engine, snapshot)
        connection = sqlite3.connect(str(snapshot))
        try:
            cursor = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
            existing = {row[0] for row in cursor.fetchall()}

            async def run_query(query: Any) -> Any:
                # The stdlib connection needs plain SQL, not a TextClause.
                return connection.execute(str(query))

            tables = await _enumerate_tables(engine, run_query, existing_tables=existing)
            for table_name in tables:
                yield table_name, _sqlite_table_rows(connection, table_name)
        finally:
            connection.close()
    finally:
        if owned_temp:
            snapshot.unlink(missing_ok=True)


def _sqlite_table_rows(
    connection: sqlite3.Connection, table: str
) -> AsyncIterator[dict[str, Any]]:
    """Batched async iterator over a snapshot table."""

    async def _gen() -> AsyncIterator[dict[str, Any]]:
        cursor = connection.execute(f'SELECT * FROM "{table}"')  # noqa: S608
        columns = [d[0] for d in cursor.description] if cursor.description else []
        while True:
            rows = cursor.fetchmany(FETCH_SIZE)
            if not rows:
                break
            for row in rows:
                yield {c: encode_value(v) for c, v in zip(columns, row)}
            await asyncio.sleep(0)

    return _gen()
