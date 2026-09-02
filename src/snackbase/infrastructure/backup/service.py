"""Backup service: builds archives and hands them to the destination.

The service owns the full sequence for one archive: acquire the
active-operation guard, snapshot the database, collect row counts, include
the local files tree when file storage is local, write the manifest, hand
the archive to the destination, and append audit entries. It works against
any :class:`BackupDestination` and any session factory, so the API, the
CLI, and the scheduler share one implementation.

In-flight state deliberately lives only in memory plus the lock file. No
``jobs`` or ``hooks`` rows are created: a backup that recorded its own
progress in the database it is snapshotting would capture a job stuck in
``running`` that returns on every restore.
"""

import secrets
import sqlite3
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from snackbase.core.config import Settings, get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.backup.archive import (
    DATA_MEMBER,
    FILES_PREFIX,
    MANIFEST_MEMBER,
    ArchiveWriter,
    copy_file_chunks,
)
from snackbase.infrastructure.backup.audit import (
    EVENT_CREATE_COMPLETED,
    EVENT_CREATE_FAILED,
    EVENT_CREATE_STARTED,
    SYSTEM_ACCOUNT_ID,
    write_backup_event,
)
from snackbase.infrastructure.backup.destinations import (
    BackupDestination,
    BackupExistsError,
    LocalBackupDestination,
)
from snackbase.infrastructure.backup.lock import backup_lock
from snackbase.infrastructure.backup.manifest import (
    BackupManifest,
    fingerprints_from_settings,
    load_alembic_heads,
    running_engine,
    snackbase_version,
)
from snackbase.infrastructure.backup.sqlite_snapshot import (
    snapshot_sqlite,
    sqlite_file_path,
)
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)

logger = get_logger(__name__)

#: Staging directory for archives under construction, inside the backup dir.
STAGING_SUBDIR = ".tmp"

#: Tables whose contents say nothing outside their instance; recorded in the
#: manifest rather than exported.
EXCLUDED_COUNT_TABLES = frozenset({"alembic_version"})


@dataclass
class BackupOutcome:
    """Result of a completed backup."""

    name: str
    size: int
    manifest: BackupManifest
    destination_type: str


def staging_dir(backup_dir: Path) -> Path:
    """The directory where archives are built before the destination handoff."""
    return Path(backup_dir) / STAGING_SUBDIR


def backup_working_dir(destination: BackupDestination) -> Path:
    """The local directory backing a destination: staging and lock files.

    For a local destination this is the destination directory itself, so the
    archive handoff is a rename. For remote destinations it is the standard
    local backup directory, which every process on the instance can see.
    """
    if isinstance(destination, LocalBackupDestination):
        return destination.base_path
    return Path("./sb_data/backups")


async def resolve_storage_mode(session: AsyncSession) -> str:
    """Determine why files may be absent: is the active file store S3?

    Reads the same ``storage_providers`` system configuration
    :class:`StorageService` uses: the default provider if one is marked,
    otherwise the first enabled provider. No configuration at all means the
    instance stores files on its local disk.
    """
    repo = ConfigurationRepository(session)
    enabled = await repo.list_configs(
        category="storage_providers",
        account_id=SYSTEM_ACCOUNT_ID,
        is_system=True,
        enabled_only=True,
    )
    if not enabled:
        return "local"
    selected = next((config for config in enabled if config.is_default), enabled[0])
    return "s3" if selected.provider_name == "s3" else "local"


def collect_row_counts(snapshot_path: Path) -> dict[str, int]:
    """Count rows per table in a snapshot database.

    Enumerates the tables that exist in the snapshot itself (core and
    dynamic), skipping SQLite internals and ``alembic_version`` — schema
    state travels in ``manifest.alembic_heads``.
    """
    connection = sqlite3.connect(str(snapshot_path))
    try:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [
            row[0] for row in cursor.fetchall() if row[0] not in EXCLUDED_COUNT_TABLES
        ]
        counts: dict[str, int] = {}
        for table in tables:
            # Table names come from the snapshot's own catalog, so they are
            # quoted as identifiers rather than bound as values.
            safe = str(table).replace('"', '""')
            row = connection.execute(f'SELECT COUNT(*) FROM "{safe}"').fetchone()
            counts[str(table)] = int(row[0]) if row else 0
        return counts
    finally:
        connection.close()


def build_manifest(
    settings: Settings,
    *,
    backup_type: str,
    storage_mode: str,
    includes_files: bool,
    table_row_counts: dict[str, int],
) -> BackupManifest:
    """Assemble a manifest for the running instance."""
    engine = running_engine(settings.database_url)
    fingerprints = fingerprints_from_settings(settings)
    return BackupManifest(
        format_version=1,
        created_at=datetime.now(UTC).isoformat(),
        snackbase_version=snackbase_version(),
        backup_type=backup_type,
        database_engine=engine,
        alembic_heads=load_alembic_heads(),
        includes_files=includes_files,
        storage_mode=storage_mode,
        encryption_key_fingerprint=fingerprints["encryption_key_fingerprint"],
        secret_key_fingerprint=fingerprints["secret_key_fingerprint"],
        token_secret_fingerprint=fingerprints["token_secret_fingerprint"],
        table_row_counts=table_row_counts,
    )


async def create_backup(
    *,
    name: str,
    destination: BackupDestination,
    session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    | None = None,
    settings: Settings | None = None,
    actor: tuple[str, str, str] | None = None,
    audit_events: bool = True,
) -> BackupOutcome:
    """Create a consistent SQLite backup archive at the destination.

    Args:
        name: Archive file name (validated by the destination).
        destination: Configured archive destination.
        session_factory: Session factory used for storage-mode detection and
            audit entries. Required when ``audit_events`` is true.
        settings: Settings override; defaults to the cached application
            settings.
        actor: ``(user_id, email, name)`` for audit entries; ``system`` when
            omitted.
        audit_events: Whether to append audit entries.

    Returns:
        The completed backup's name, byte size, and manifest.
    """
    settings = settings or get_settings()
    working_dir = backup_working_dir(destination)
    user_id, user_email, user_name = actor or ("system", "system", "system")

    async def audit(event: str, **kwargs: object) -> None:
        if not audit_events or session_factory is None:
            return
        await write_backup_event(
            session_factory,
            event=event,
            name=name,
            destination_type=_destination_kind(destination),
            actor_user_id=user_id,
            actor_email=user_email,
            actor_name=user_name,
            **kwargs,  # type: ignore[arg-type]
        )

    await audit(EVENT_CREATE_STARTED)
    try:
        async with backup_lock(name, "backup", working_dir):
            if await destination.exists(name):
                raise BackupExistsError(f"Archive already exists: {name}")
            outcome = await _run_backup(
                name=name,
                destination=destination,
                working_dir=working_dir,
                session_factory=session_factory,
                settings=settings,
            )
    except Exception as exc:
        await audit(
            EVENT_CREATE_FAILED,
            extra={"error": str(exc)[:2000]},
        )
        raise
    await audit(EVENT_CREATE_COMPLETED, size=outcome.size)
    return outcome


async def _run_backup(
    *,
    name: str,
    destination: BackupDestination,
    working_dir: Path,
    session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    | None,
    settings: Settings,
) -> BackupOutcome:
    staging = staging_dir(working_dir)
    staging.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(8)
    snapshot_path = staging / f"{token}.db"
    archive_path = staging / f"{token}.zip"

    storage_mode = "local"
    if session_factory is not None:
        async with session_factory() as session:
            storage_mode = await resolve_storage_mode(session)
    includes_files = storage_mode == "local"

    # Refuse non-SQLite engines before touching the destination: PostgreSQL
    # disaster recovery is configured on the database, not here.
    sqlite_file_path(settings.database_url)

    engine = create_async_engine(settings.database_url)
    try:
        await snapshot_sqlite(engine, snapshot_path)

        counts = collect_row_counts(snapshot_path)
        manifest = build_manifest(
            settings,
            backup_type="sqlite_physical",
            storage_mode=storage_mode,
            includes_files=includes_files,
            table_row_counts=counts,
        )

        with ArchiveWriter(archive_path) as writer:
            writer.write_text_member(MANIFEST_MEMBER, manifest.to_json())
            # Stream the snapshot in chunks: the database may be far larger
            # than process memory.
            with (
                open(snapshot_path, "rb") as source,
                writer.open_member(DATA_MEMBER) as member,
            ):
                copy_file_chunks(source, member)
            if includes_files:
                storage_path = Path(settings.storage_path)
                writer.write_file_tree(
                    storage_path,
                    FILES_PREFIX,
                    skip={working_dir, staging, storage_path / STAGING_SUBDIR},
                )

        await destination.write(name, archive_path)
    finally:
        await engine.dispose()
        for leftover in (snapshot_path, archive_path):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:  # pragma: no cover - best-effort cleanup
                logger.warning("Failed to remove staging file", path=str(leftover))

    entries = await destination.list()
    size = next((entry.size for entry in entries if entry.name == name), 0)
    logger.info(
        "Backup archive created",
        archive=name,
        destination=_destination_kind(destination),
        size=size,
    )
    return BackupOutcome(
        name=name,
        size=size,
        manifest=manifest,
        destination_type=_destination_kind(destination),
    )


def _destination_kind(destination: BackupDestination) -> str:
    """``"local"`` or ``"s3"`` — the destination_type recorded in audits."""
    return "s3" if not isinstance(destination, LocalBackupDestination) else "local"


def generate_backup_name(prefix: str = "snackbase_backup_") -> str:
    """A timestamped archive name: ``<prefix><UTC yyyymmddHHMMSS>.zip``."""
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}{stamp}.zip"
