"""Restore/migration integration: the swap must survive a real ``upgrade heads``.

The regression guard for the interaction between restore and the dynamic
Alembic branch. Every test here runs the same migration command boot runs
(``command.upgrade(cfg, "heads")``) *after* ``execute_pending_restore`` and
asserts the restored schema survived — the check F3.2 specified and that was
missing when restore silently dropped or bricked restored collections.
"""

import asyncio
import sqlite3
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from snackbase.core.config import Settings
from snackbase.infrastructure.backup.destinations import LocalBackupDestination
from snackbase.infrastructure.backup.restore import (
    execute_pending_restore,
    finalize_restore,
    write_marker,
)
from snackbase.infrastructure.backup.service import create_backup
from snackbase.infrastructure.persistence.migration_service import (
    MigrationService,
    dynamic_migrations_dir,
)


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'sb_data' / 'snackbase.db'}",
        storage_path=str(tmp_path / "sb_data" / "files"),
        _env_file=None,
    )


def _run_alembic_upgrade(database_url: str, revision: str = "heads") -> None:
    """Run exactly the migration command boot runs after the swap."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, revision)


def _db_rows(db_path: Path, table: str) -> int:
    connection = sqlite3.connect(str(db_path))
    try:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
        return int(row[0]) if row else 0
    finally:
        connection.close()


def _db_revisions(db_path: Path) -> list[str]:
    connection = sqlite3.connect(str(db_path))
    try:
        rows = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
        return sorted(str(row[0]) for row in rows)
    finally:
        connection.close()


PRODUCT_SCHEMA = [
    {"name": "name", "type": "text", "required": True},
    {"name": "sku", "type": "text", "unique": True},
]

TASK_SCHEMA = [{"name": "title", "type": "text", "required": True}]


async def _seed_instance(
    tmp_path: Path, settings: Settings
) -> tuple[MigrationService, str, str]:
    """Core migrations + two collections with records: the pre-backup state."""
    (tmp_path / "sb_data").mkdir(parents=True, exist_ok=True)
    await asyncio.get_running_loop().run_in_executor(
        None, _run_alembic_upgrade, settings.database_url
    )
    service = MigrationService(database_url=settings.database_url)
    rev_products = await asyncio.get_running_loop().run_in_executor(
        None, service.generate_create_collection_migration, "products", PRODUCT_SCHEMA
    )
    await asyncio.get_running_loop().run_in_executor(
        None, service.generate_create_collection_migration, "tasks", TASK_SCHEMA
    )
    await service.apply_migrations()

    db_path = tmp_path / "sb_data" / "snackbase.db"
    connection = sqlite3.connect(str(db_path))
    try:
        for index in range(3):
            connection.execute(
                "INSERT INTO col_products (id, account_id, created_by, updated_by, name, sku) "
                "VALUES (?, '00000000-0000-0000-0000-000000000000', 'u', 'u', ?, ?)",
                (f"p{index}", f"Product {index}", f"SKU-{index}"),
            )
        for index in range(2):
            connection.execute(
                "INSERT INTO col_tasks (id, account_id, created_by, updated_by, title) "
                "VALUES (?, '00000000-0000-0000-0000-000000000000', 'u', 'u', ?)",
                (f"t{index}", f"Task {index}"),
            )
        connection.commit()
    finally:
        connection.close()
    return service, rev_products, _latest_dynamic_head()


def _latest_dynamic_head() -> str:
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = [
        head
        for head in script.get_heads()
        if head in {p.name.split("_", 1)[0] for p in dynamic_migrations_dir().glob("*.py")}
    ]
    assert heads, "expected a dynamic branch head after generating migrations"
    return heads[0]


async def _drop_collections(service: MigrationService, names: list[str]) -> None:
    """Simulate deleting collections through the app: drop-table migrations."""
    loop = asyncio.get_running_loop()
    for name in names:
        await loop.run_in_executor(
            None, service.generate_delete_collection_migration, name
        )
    await service.apply_migrations()


@pytest_asyncio.fixture
async def session_factory(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'sb_data' / 'snackbase.db'}"
    )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_restore_survives_stale_delete_migrations(
    tmp_path: Path, session_factory
) -> None:
    """Restore replayed delete-migrations must not drop the restored tables.

    Regression for the silent data loss: backup with collections, delete the
    collections (writing drop-table migrations), restore. The archive carries
    its own migration history, so the boot's ``upgrade heads`` is a no-op on
    the dynamic branch and the restored tables survive.
    """
    settings = _make_settings(tmp_path)
    db_path = tmp_path / "sb_data" / "snackbase.db"
    service, _, dynamic_head = await _seed_instance(tmp_path, settings)
    backups_dir = tmp_path / "backups"
    await create_backup(
        name="e2e.zip",
        destination=LocalBackupDestination(backups_dir),
        settings=settings,
    )

    # Delete both collections the way the app does: drop-table migrations.
    await _drop_collections(service, ["tasks", "products"])
    assert not (db_path.parent / "col_products").exists()

    write_marker(
        settings,
        archive_name="e2e.zip",
        destination={"type": "local", "local_path": str(backups_dir)},
        requested_by="system",
        manifest_fingerprints={},
    )
    assert execute_pending_restore(settings) is not None

    # Boot's migration run: with the archive's own history in place this is
    # a dynamic-branch no-op, and it must not raise.
    await asyncio.get_running_loop().run_in_executor(
        None, _run_alembic_upgrade, settings.database_url
    )

    assert _db_rows(db_path, "col_products") == 3
    assert _db_rows(db_path, "col_tasks") == 2
    # The archive's dynamic head is current; the delete-migrations written
    # after the backup never replayed.
    assert dynamic_head in _db_revisions(db_path)

    result = await finalize_restore(settings, session_factory)
    assert result is not None
    assert result.status == "completed"
    assert result.warnings == []


@pytest.mark.asyncio
async def test_restore_over_fresh_instance_boots(
    tmp_path: Path, session_factory
) -> None:
    """The cleanup_dev scenario: no local migrations, archive provides them.

    A fresh instance has no dynamic migration files, so the restored
    database's dynamic revision was previously unresolvable and the boot
    died with ``Can't locate revision``. The archive now carries the
    scripts the restored database refers to.
    """
    settings = _make_settings(tmp_path)
    db_path = tmp_path / "sb_data" / "snackbase.db"
    service, _, dynamic_head = await _seed_instance(tmp_path, settings)
    backups_dir = tmp_path / "backups"
    await create_backup(
        name="fresh.zip",
        destination=LocalBackupDestination(backups_dir),
        settings=settings,
    )

    # Simulate cleanup_dev.py: wipe the dynamic migrations directory.
    dynamic_dir = dynamic_migrations_dir()
    for entry in dynamic_dir.iterdir():
        if entry.is_file():
            entry.unlink()

    write_marker(
        settings,
        archive_name="fresh.zip",
        destination={"type": "local", "local_path": str(backups_dir)},
        requested_by="system",
        manifest_fingerprints={},
    )
    assert execute_pending_restore(settings) is not None

    # Boot's migration run: previously ``Can't locate revision``.
    await asyncio.get_running_loop().run_in_executor(
        None, _run_alembic_upgrade, settings.database_url
    )

    assert _db_rows(db_path, "col_products") == 3
    assert _db_rows(db_path, "col_tasks") == 2
    assert dynamic_head in _db_revisions(db_path)
    # The archive's migration scripts were restored with the database.
    assert (dynamic_dir / f"{dynamic_head}_create_collection_tasks.py").exists()

    result = await finalize_restore(settings, session_factory)
    assert result is not None
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_manifest_records_database_revisions(tmp_path: Path) -> None:
    """The manifest's ``database_revisions`` come from the snapshot DB."""
    settings = _make_settings(tmp_path)
    db_path = tmp_path / "sb_data" / "snackbase.db"
    await _seed_instance(tmp_path, settings)
    backups_dir = tmp_path / "backups"

    outcome = await create_backup(
        name="revisions.zip",
        destination=LocalBackupDestination(backups_dir),
        settings=settings,
    )

    assert set(outcome.manifest.database_revisions) == set(
        _db_revisions(db_path)
    )
    assert outcome.manifest.includes_migrations is True
    assert outcome.manifest.format_version == 2
