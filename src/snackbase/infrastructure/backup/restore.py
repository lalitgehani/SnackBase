"""Pre-boot restore: the data swap happens before any database connection.

The API (or CLI) validates an archive, writes a marker file beside the
SQLite database, and exits. The supervisor restarts the process; at
startup — before the database engine is created and before migrations run
— the marker is detected and the swap performed. Nothing holds the database
open during the swap because nothing has opened it yet. The marker file is
the transaction record: a crash mid-restore is recovered by retrying on the
next boot rather than by unwinding.

The swap covers every piece of instance schema state: the database file,
the uploaded files tree, and the dynamic collection migrations in
``sb_data/migrations/``. The restored database's ``alembic_version`` refers
to those scripts, so they must travel with it — the boot that follows then
runs ``upgrade heads`` against a script directory that provably matches the
database, and new core migrations from a newer binary still apply normally.

The executor stops at the swap: it records status ``swapped`` and the boot
path calls :func:`finalize_restore` after migrations have run to verify the
restored schema and promote the outcome to ``completed``. A ``completed``
outcome therefore always means the instance actually booted.
"""

import json
import os
import shutil
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snackbase.core.config import Settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.backup.archive import (
    DATA_MEMBER,
    FILES_PREFIX,
    MANIFEST_MEMBER,
    MIGRATIONS_PREFIX,
    member_names,
    validate_member_paths,
)
from snackbase.infrastructure.backup.destinations import (
    BackupDestination,
    BackupNotFoundError,
    LocalBackupDestination,
    S3BackupDestination,
    UnsupportedEngineError,
)
from snackbase.infrastructure.backup.manifest import (
    BackupManifest,
    CompatibilityIssue,
    running_engine,
)

logger = get_logger(__name__)

MARKER_FILENAME = ".restore-pending.json"
MARKER_INVALID_SUFFIX = ".invalid"
MARKER_FAILED_SUFFIX = ".failed"
LAST_RESTORE_FILENAME = ".restore-last.json"
RESTORE_OLD_DIRNAME = ".restore_old"
RESTORE_TMP_DIRNAME = ".restore_tmp"
EXTRACT_SUBDIR = "extracted"
RESTORE_MANIFEST_FILENAME = ".restore-manifest.json"
BOOT_LOCK_FILENAME = ".restore.lock"
#: Sentinel inside a preserved ``.restore_old/<ts>/`` directory: present only
#: while its swap is in flight. A snapshot without it is a deliberate
#: post-success retention, not an interrupted attempt.
IN_PROGRESS_SENTINEL = ".in-progress"


class RestoreAbortedError(RuntimeError):
    """Raised when a restore request or a pending restore cannot proceed."""


class RestoreTerminalError(RestoreAbortedError):
    """A pending restore that can never succeed, even on a later boot.

    A missing archive, an unreadable archive, a member-path escape, a disk
    shortfall, or a fingerprint mismatch is not fixed by restarting: the
    executor renames the marker to ``.restore-pending.json.failed``, records
    the failure, and lets boot continue on the untouched original data. Only
    transient failures (destination resolution, network reads) and failures
    at or after the swap keep the marker for the retry-on-next-boot path.
    """


@dataclass
class RestoreValidation:
    """Structured result of pre-restore compatibility checking."""

    manifest: BackupManifest
    blocking: list[CompatibilityIssue]
    warnings: list[CompatibilityIssue]


@dataclass
class RestoreResult:
    """Outcome of a restore, persisted to ``.restore-last.json``.

    ``swapped`` is written by the boot-time executor: the data is in place
    but migrations have not run yet, so the instance is not verified.
    :func:`finalize_restore` promotes it after migrations to ``completed``
    (or ``completed_with_warnings``).
    """

    archive_name: str
    status: str  # "swapped" | "completed" | "completed_with_warnings" | "failed"
    completed_at: str
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def data_dir(settings: Settings) -> Path:
    """The directory beside the SQLite database file.

    The marker lives here — not in the backup directory — so it is found at
    boot regardless of destination configuration.
    """
    return database_path(settings).parent


def database_path(settings: Settings) -> Path:
    from snackbase.infrastructure.backup.sqlite_snapshot import sqlite_file_path

    return Path(sqlite_file_path(settings.database_url)).resolve()


def marker_path(settings: Settings) -> Path:
    return data_dir(settings) / MARKER_FILENAME


def last_restore_path(settings: Settings) -> Path:
    return data_dir(settings) / LAST_RESTORE_FILENAME


def restore_manifest_copy_path(settings: Settings) -> Path:
    """Where the executor stashes the archive manifest for finalize."""
    return data_dir(settings) / RESTORE_MANIFEST_FILENAME


def dynamic_migrations_path(settings: Settings) -> Path:
    """The instance's dynamic collection-migration directory.

    Resolved from the Alembic config (``version_locations``), the same
    source migration generation uses, so the swap can never target a
    different directory than the one migrations are written to.
    """
    from snackbase.infrastructure.persistence.migration_service import (
        dynamic_migrations_dir,
    )

    return dynamic_migrations_dir()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Marker
# ---------------------------------------------------------------------------


def write_marker(
    settings: Settings,
    *,
    archive_name: str,
    destination: dict[str, Any],
    requested_by: str,
    manifest_fingerprints: dict[str, str],
) -> dict[str, Any]:
    """Write the pending-restore marker; its contents are the 202 payload."""
    payload: dict[str, Any] = {
        "archive_name": archive_name,
        "destination": destination,
        "requested_by": requested_by,
        "requested_at": _utc_now_iso(),
        "manifest_fingerprints": manifest_fingerprints,
    }
    path = marker_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Restore marker written", archive=archive_name, path=str(path))
    return payload


def read_marker(settings: Settings) -> dict[str, Any] | None:
    """Read and parse the marker, or None when absent or malformed.

    A malformed marker is renamed to ``.restore-pending.json.invalid`` and
    boot continues normally.
    """
    path = marker_path(settings)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("marker must be a JSON object")
        if not isinstance(payload.get("archive_name"), str):
            raise ValueError("marker is missing archive_name")
        if not isinstance(payload.get("destination"), dict):
            raise ValueError("marker is missing destination")
        return payload
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        invalid = path.with_name(MARKER_FILENAME + MARKER_INVALID_SUFFIX)
        logger.warning(
            "Malformed restore marker — renaming and continuing boot",
            path=str(path),
            error=str(exc),
        )
        try:
            path.rename(invalid)
        except OSError:  # pragma: no cover - best-effort
            pass
        return None


def destination_to_marker_dict(
    destination: BackupDestination, settings: Settings
) -> dict[str, Any]:
    """Snapshot the destination configuration into the marker.

    The S3 secret is stored encrypted: the fingerprint check makes the
    encryption key a precondition of the restore, so the boot-time executor
    can always decrypt it with the current key.
    """
    if isinstance(destination, S3BackupDestination):
        ciphertext = None
        if destination.secret_access_key:
            from snackbase.infrastructure.security.encryption import EncryptionService

            ciphertext = EncryptionService(settings.encryption_key).encrypt(
                destination.secret_access_key
            )
        return {
            "type": "s3",
            "bucket": destination.bucket,
            "region": destination.region,
            "access_key_id": destination.access_key_id,
            "s3_secret_access_key_ciphertext": ciphertext,
            "key_prefix": destination.key_prefix,
            "endpoint_url": destination.endpoint_url,
        }
    if isinstance(destination, LocalBackupDestination):
        return {"type": "local", "local_path": str(destination.base_path)}
    return {"type": "unknown"}


def destination_from_marker(
    marker: dict[str, Any], settings: Settings
) -> BackupDestination:
    """Rebuild the destination recorded in the marker."""
    destination = marker.get("destination", {})
    kind = str(destination.get("type", "local"))
    if kind == "local":
        return LocalBackupDestination(str(destination.get("local_path", "")))
    if kind == "s3":
        ciphertext = destination.get("s3_secret_access_key_ciphertext")
        secret_plain = None
        if ciphertext:
            from snackbase.infrastructure.security.encryption import EncryptionService

            secret_plain = EncryptionService(settings.encryption_key).decrypt(
                str(ciphertext)
            )
        return S3BackupDestination(
            bucket=str(destination.get("bucket", "")),
            region=str(destination.get("region", "us-east-1")),
            access_key_id=destination.get("access_key_id") or None,
            secret_access_key=secret_plain,
            key_prefix=str(destination.get("key_prefix", "")),
            endpoint_url=str(destination.get("endpoint_url")) or None,
        )
    raise RestoreAbortedError(f"Unknown destination type in restore marker: {kind!r}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_restore_candidate(
    destination: BackupDestination,
    name: str,
    settings: Settings,
    *,
    current_storage_mode: str | None = None,
) -> RestoreValidation:
    """Validate an archive for restore without touching any live state.

    Fetches the archive to a scratch location, checks the zip layout and
    manifest, and runs the compatibility check against current settings.
    ``current_storage_mode`` enables the storage-mode mismatch warning when
    the caller has a session to read the storage configuration.

    Raises:
        BackupNotFoundError: The archive does not exist at the destination.
        ValueError: Not a zip, missing ``manifest.json``/``data.db``, an
            unparsable manifest, an unsupported manifest format version, or
            a backup directory configured inside the files storage path.
    """
    _check_backup_dir_outside_storage(destination, settings)
    scratch = data_dir(settings) / RESTORE_TMP_DIRNAME
    scratch.mkdir(parents=True, exist_ok=True)
    local_copy = scratch / f"validate-{uuid.uuid4().hex}.zip"
    try:
        destination.read_sync(name, local_copy)
        manifest = _parse_manifest(local_copy, name)
        issues = manifest.verify_compatibility(
            settings, current_storage_mode=current_storage_mode
        )
        return RestoreValidation(
            manifest=manifest,
            blocking=[i for i in issues if i.severity == "blocking"],
            warnings=[i for i in issues if i.severity == "warning"],
        )
    finally:
        # local_copy is a file: unlink it. (rmtree on a file silently
        # no-ops with ignore_errors and leaked a full archive per call.)
        local_copy.unlink(missing_ok=True)


def _check_backup_dir_outside_storage(
    destination: BackupDestination, settings: Settings
) -> None:
    """Refuse when the local backup directory sits inside the files tree.

    Restoring moves the whole storage path into ``.restore_old`` — a backup
    directory nested inside it would be destroyed along with the data it
    protects. The backup side already skips such a directory when writing;
    the restore side refuses outright.

    Raises:
        ValueError: When a local destination resolves inside
            ``settings.storage_path``.
    """
    if not isinstance(destination, LocalBackupDestination):
        return
    backup_dir = Path(destination.base_path).resolve()
    storage = Path(settings.storage_path).resolve()
    if backup_dir == storage or storage in backup_dir.parents:
        raise ValueError(
            f"Backup directory {backup_dir} is inside the file storage path "
            f"{storage}. Restoring would destroy the archives; move the "
            "backup destination outside the storage path and retry."
        )


def _parse_manifest(archive_file: Path, name: str) -> BackupManifest:
    try:
        names = member_names(archive_file)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"Archive {name} is not a readable zip: {exc}") from exc
    for member in (MANIFEST_MEMBER, DATA_MEMBER):
        if member not in names:
            raise ValueError(f"Archive {name} is missing {member}")
    try:
        with zipfile.ZipFile(archive_file) as archive:
            payload = archive.read(MANIFEST_MEMBER)
        return BackupManifest.from_json(payload.decode("utf-8"))
    except (zipfile.BadZipFile, OSError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"Archive {name} has an unreadable manifest: {exc}"
        ) from exc


def check_engine_is_sqlite(settings: Settings) -> None:
    """Refuse restore on PostgreSQL with a pointer at database-side recovery.

    Raises:
        RestoreAbortedError: When the running engine is not SQLite.
    """
    from snackbase.infrastructure.backup.sqlite_snapshot import sqlite_file_path

    try:
        sqlite_file_path(settings.database_url)
    except UnsupportedEngineError as exc:
        raise RestoreAbortedError(
            "Restore is supported on SQLite instances only. This instance "
            "runs PostgreSQL: configure disaster recovery on the database "
            "itself (managed snapshots or operator-run pg_dump)."
        ) from exc


# ---------------------------------------------------------------------------
# Last-restore outcome
# ---------------------------------------------------------------------------


def record_last_restore(settings: Settings, result: RestoreResult) -> None:
    """Persist the last restore outcome for the restore-status endpoint."""
    path = data_dir(settings) / LAST_RESTORE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def read_last_restore(settings: Settings) -> RestoreResult | None:
    path = data_dir(settings) / LAST_RESTORE_FILENAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        warnings = data.get("warnings") or []
        return RestoreResult(
            archive_name=str(data.get("archive_name", "unknown")),
            status=str(data.get("status", "unknown")),
            completed_at=str(data.get("completed_at", "")),
            error=data.get("error"),
            warnings=[str(w) for w in warnings] if isinstance(warnings, list) else [],
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Boot-time executor
# ---------------------------------------------------------------------------


def _claim_boot_lock(settings: Settings) -> int | None:
    """Claim the boot-time restore lock with ``O_CREAT | O_EXCL``.

    A deployment may run ``serve`` and ``worker`` as separate supervised
    processes; a restart brings both up at once and both would otherwise
    perform the same swap concurrently. Returns the lock's file descriptor,
    or None when another live process holds it. A lock whose holder is dead
    is swept and reclaimed — a kill -9 mid-swap must not wedge every boot.
    """
    from snackbase.infrastructure.backup.lock import _pid_running

    path = data_dir(settings) / BOOT_LOCK_FILENAME
    payload = json.dumps({"pid": os.getpid(), "started_at": _utc_now_iso()})
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, payload.encode("utf-8"))
            return fd
        except FileExistsError:
            pass
        except OSError as exc:  # pragma: no cover - unusual filesystems
            logger.warning("Could not claim restore boot lock", error=str(exc))
            return None
        holder_pid = 0
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
            holder_pid = int(info.get("pid", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            holder_pid = 0
        if _pid_running(holder_pid):
            return None
        try:
            path.unlink()
        except OSError:  # pragma: no cover - best-effort
            return None


def _release_boot_lock(settings: Settings, fd: int | None) -> None:
    if fd is not None:
        os.close(fd)
    try:
        (data_dir(settings) / BOOT_LOCK_FILENAME).unlink(missing_ok=True)
    except OSError:  # pragma: no cover - best-effort
        pass


def execute_pending_restore(settings: Settings) -> RestoreResult | None:
    """Perform the pending restore before anything opens the database.

    Returns None when no marker exists (normal boot; also prunes expired
    ``.restore_old`` data and leaked ``.restore_tmp`` scratch). On success
    the database, files, and dynamic migrations have been replaced, the
    marker removed, and the previous data preserved under
    ``.restore_old/<timestamp>/``; the recorded status is ``swapped`` and
    the caller finalizes it after migrations. Transient failures roll
    everything back, leave the marker in place, and raise
    :class:`RestoreAbortedError` so the caller aborts boot with a non-zero
    exit. Terminal failures — an archive that can never restore — rename
    the marker to ``.restore-pending.json.failed``, record the failure, and
    return None so boot continues on the untouched original data instead of
    wedging every future boot.
    """
    # First statement, before anything resolves paths from the database URL:
    # the executor runs on every boot and must be a no-op on PostgreSQL.
    if running_engine(settings.database_url) != "sqlite":
        return None

    marker = read_marker(settings)
    if marker is None:
        _cleanup_old_data(settings)
        _sweep_restore_tmp(settings)
        return None

    boot_lock_fd = _claim_boot_lock(settings)
    if boot_lock_fd is None:
        raise RestoreAbortedError(
            "Another process is performing the pending restore; restart "
            "again once it finishes."
        )
    try:
        return _execute_pending_restore_locked(settings, marker)
    finally:
        _release_boot_lock(settings, boot_lock_fd)


def _execute_pending_restore_locked(
    settings: Settings, marker: dict[str, Any]
) -> RestoreResult | None:
    archive_name = str(marker["archive_name"])
    if _has_interrupted_attempt(settings):
        # A previous boot died mid-restore. Its preserved data is the
        # authoritative current state: roll it back, then retry the restore.
        logger.info(
            "Interrupted restore attempt detected; rolling back before retrying",
            archive=archive_name,
        )
        _rollback_interrupted_attempt(settings)

    working = data_dir(settings)
    tmp_dir = working / RESTORE_TMP_DIRNAME
    archive_local = tmp_dir / f"{uuid.uuid4().hex}.zip"
    extract_dir = tmp_dir / EXTRACT_SUBDIR

    logger.info("Starting restore", archive=archive_name)
    try:
        try:
            destination = destination_from_marker(marker, settings)
        except RestoreTerminalError:
            raise
        except Exception as exc:
            raise RestoreAbortedError(
                f"Cannot resolve destination for restore: {exc}"
            ) from exc

        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            destination.read_sync(archive_name, archive_local)
        except BackupNotFoundError as exc:
            raise RestoreTerminalError(
                f"Archive {archive_name} no longer exists at the destination"
            ) from exc

        _check_free_space(working, archive_local)

        try:
            names = member_names(archive_local)
            validate_member_paths(names)
        except ValueError as exc:
            # A structurally unsafe archive will not become safe on reboot.
            raise RestoreTerminalError(str(exc)) from exc
        if MANIFEST_MEMBER not in names or DATA_MEMBER not in names:
            raise RestoreTerminalError(
                f"Archive {archive_name} is missing {MANIFEST_MEMBER} or {DATA_MEMBER}"
            )
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_local) as archive:
            archive.extractall(extract_dir)
        logger.info("Archive extracted", archive=archive_name)

        # Re-verify fingerprints: the environment may have changed between
        # request and boot. A mismatch is terminal — rebooting cannot
        # reconcile the keys.
        try:
            manifest = BackupManifest.from_json(
                (extract_dir / MANIFEST_MEMBER).read_text(encoding="utf-8")
            )
        except ValueError as exc:
            raise RestoreTerminalError(
                f"Archive {archive_name} has an unreadable manifest: {exc}"
            ) from exc
        issues = manifest.verify_compatibility(settings)
        blocking = [issue for issue in issues if issue.severity == "blocking"]
        if blocking:
            raise RestoreTerminalError(
                "Archive fingerprints no longer match this instance: "
                + "; ".join(issue.message for issue in blocking)
            )

        db_path = database_path(settings)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        old_dir = working / RESTORE_OLD_DIRNAME / stamp
        old_dir.mkdir(parents=True, exist_ok=True)
        _preserve_current_data(
            settings, db_path, old_dir, include_files=manifest.includes_files
        )

        try:
            _swap_restored_data(settings, extract_dir, db_path, manifest)
            logger.info("Data swap complete", archive=archive_name)
        except Exception as exc:
            # The swap failed: put the old data back and leave the marker so
            # the next boot retries.
            _rollback_old_data(settings, db_path, old_dir)
            raise RestoreAbortedError(f"Data swap failed: {exc}") from exc

        # Success: the marker is the transaction record — remove it, stash
        # the manifest for finalize's verification, and record ``swapped``.
        # Migrations have not run yet; only the post-migration finalize may
        # promote this to ``completed``.
        sentinel = old_dir / IN_PROGRESS_SENTINEL
        sentinel.unlink(missing_ok=True)
        marker_path(settings).unlink(missing_ok=True)
        shutil.copy(
            extract_dir / MANIFEST_MEMBER,
            restore_manifest_copy_path(settings),
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _cleanup_old_data(settings, keep_most_recent=True)
        result = RestoreResult(
            archive_name=archive_name,
            status="swapped",
            completed_at=_utc_now_iso(),
        )
        record_last_restore(settings, result)
        logger.info(
            "Restore swapped; outcome finalized after migrations",
            archive=archive_name,
        )
        return result

    except RestoreTerminalError as exc:
        # Rebooting cannot fix this: retire the marker so boot continues on
        # the original data instead of wedging every future start.
        record_last_restore(
            settings,
            RestoreResult(
                archive_name=archive_name,
                status="failed",
                completed_at=_utc_now_iso(),
                error=str(exc),
            ),
        )
        mark_audit_pending(settings, "backup.restore.failed", archive_name)
        failed_marker = marker_path(settings).with_name(
            MARKER_FILENAME + MARKER_FAILED_SUFFIX
        )
        try:
            marker_path(settings).rename(failed_marker)
        except OSError:  # pragma: no cover - best-effort
            marker_path(settings).unlink(missing_ok=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.error(
            "Restore failed terminally; marker retired and boot continuing",
            archive=archive_name,
            error=str(exc),
        )
        return None
    except RestoreAbortedError as exc:
        record_last_restore(
            settings,
            RestoreResult(
                archive_name=archive_name,
                status="failed",
                completed_at=_utc_now_iso(),
                error=str(exc),
            ),
        )
        mark_audit_pending(settings, "backup.restore.failed", archive_name)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.error("Restore failed", archive=archive_name, error=str(exc))
        raise
    except Exception as exc:
        record_last_restore(
            settings,
            RestoreResult(
                archive_name=archive_name,
                status="failed",
                completed_at=_utc_now_iso(),
                error=str(exc),
            ),
        )
        mark_audit_pending(settings, "backup.restore.failed", archive_name)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.error(
            "Restore failed unexpectedly", archive=archive_name, error=str(exc)
        )
        raise RestoreAbortedError(f"Restore failed: {exc}") from exc


def _swap_restored_data(
    settings: Settings,
    extract_dir: Path,
    db_path: Path,
    manifest: BackupManifest,
) -> None:
    """Move the restored database, migrations, and files into place.

    The dynamic migration directory is replaced — not merged — because the
    restored database's ``alembic_version`` refers to exactly the history
    the archive carries. An archive that includes an empty dynamic branch
    clears the local directory: an empty history is a real state.
    """
    shutil.move(str(extract_dir / DATA_MEMBER), str(db_path))

    dynamic_dir = dynamic_migrations_path(settings)
    if dynamic_dir.exists():
        shutil.rmtree(dynamic_dir)
    if manifest.includes_migrations:
        extracted_migrations = extract_dir / MIGRATIONS_PREFIX.rstrip("/")
        if extracted_migrations.is_dir():
            dynamic_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted_migrations), str(dynamic_dir))

    if manifest.includes_files:
        extracted_files = extract_dir / FILES_PREFIX.rstrip("/")
        storage = Path(settings.storage_path)
        if extracted_files.is_dir():
            if storage.exists():
                shutil.rmtree(storage)
            storage.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted_files), str(storage))


async def finalize_restore(
    settings: Settings, session_factory: Any
) -> RestoreResult | None:
    """Verify a swapped restore after migrations and record the outcome.

    Called by every boot path (``serve`` and ``worker``) after
    ``init_database()``. Compares the archived manifest's table row counts
    against the live database: a missing table or a count drift means the
    post-swap migration run damaged the restore, which surfaces as
    ``completed_with_warnings`` instead of a silent ``completed``. Writes
    the restore audit entry into the restored database — the correct place
    for it, now that the database is available here.

    Returns the final result, or None when there is nothing to finalize.
    """
    from snackbase.infrastructure.backup.audit import (
        EVENT_RESTORE_COMPLETED,
        write_backup_event,
    )

    last = read_last_restore(settings)
    if last is None or last.status != "swapped":
        return None

    warnings: list[str] = []
    manifest_copy = restore_manifest_copy_path(settings)
    if manifest_copy.is_file():
        try:
            manifest = BackupManifest.from_json(
                manifest_copy.read_text(encoding="utf-8")
            )
        except ValueError as exc:
            manifest = None
            warnings.append(
                f"Restored manifest could not be read for verification: {exc}"
            )
    else:
        manifest = None
        warnings.append(
            "Restored manifest copy was not found; verification skipped."
        )

    if manifest is not None:
        async with session_factory() as session:
            warnings.extend(await _verify_restored_tables(session, manifest))

    status = "completed_with_warnings" if warnings else "completed"
    result = RestoreResult(
        archive_name=last.archive_name,
        status=status,
        completed_at=_utc_now_iso(),
        error=None,
        warnings=warnings,
    )
    record_last_restore(settings, result)
    manifest_copy.unlink(missing_ok=True)

    try:
        await write_backup_event(
            session_factory,
            event=EVENT_RESTORE_COMPLETED,
            name=last.archive_name,
            destination_type="",
            extra={"warnings": warnings} if warnings else None,
        )
    except Exception as exc:  # noqa: BLE001 - never block boot on audit
        logger.error("Failed to write restore audit entry", error=str(exc))

    logger.info(
        "Restore finalized",
        archive=last.archive_name,
        status=status,
        warnings=len(warnings),
    )
    return result


async def _verify_restored_tables(session: Any, manifest: BackupManifest) -> list[str]:
    """Compare the archive's table row counts against the live database."""
    from sqlalchemy import text

    warnings: list[str] = []
    result = await session.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    )
    live_tables = {str(row[0]) for row in result.fetchall()}
    for table, expected in sorted(manifest.table_row_counts.items()):
        if table not in live_tables:
            warnings.append(
                f"Table {table!r} from the archive is missing after the restore."
            )
            continue
        safe = table.replace('"', '""')
        row = await session.execute(text(f'SELECT COUNT(*) FROM "{safe}"'))
        live_count = int(row.scalar() or 0)
        if live_count != expected:
            warnings.append(
                f"Table {table!r} has {live_count} rows after the restore; "
                f"the archive recorded {expected}."
            )
    extras = sorted(
        live_tables - set(manifest.table_row_counts) - {"alembic_version"}
    )
    if extras:
        warnings.append(
            "Unexpected tables after the restore: " + ", ".join(extras)
        )
    return warnings


def _check_free_space(working: Path, archive_local: Path) -> None:
    """Warn at and abort below twice the archive size in free disk space."""
    required = archive_local.stat().st_size * 2
    try:
        free = shutil.disk_usage(str(working)).free
    except OSError:  # pragma: no cover - unusual filesystems
        return
    if free < required:
        raise RestoreTerminalError(
            f"Insufficient free disk space for restore: {free} bytes free, "
            f"{required} bytes required (2x the archive size). "
            "Free space and retry."
        )
    if free < required * 2:
        logger.warning(
            "Free disk space is below 4x the archive size during restore",
            free_bytes=free,
            archive_bytes=archive_local.stat().st_size,
        )


def _preserve_current_data(
    settings: Settings,
    db_path: Path,
    old_dir: Path,
    *,
    include_files: bool,
) -> None:
    """Move the current database (with -wal/-shm), migrations, and files aside.

    The files tree moves only when the archive will replace it: an archive
    taken with S3 storage carries no ``files/`` members, and moving a local
    tree aside for one would strand it in ``.restore_old``. The dynamic
    migrations directory always moves — the restored database replaces the
    history those scripts belong to.
    """
    for suffix in ("", "-wal", "-shm"):
        sibling = Path(str(db_path) + suffix)
        if sibling.exists():
            shutil.move(str(sibling), str(Path(old_dir) / f"data.db{suffix}"))
    dynamic_dir = dynamic_migrations_path(settings)
    if dynamic_dir.is_dir():
        shutil.move(str(dynamic_dir), str(Path(old_dir) / "migrations"))
    if include_files:
        storage = Path(settings.storage_path)
        if storage.is_dir():
            shutil.move(str(storage), str(Path(old_dir) / "files"))
    # Written last: the sentinel marks this snapshot as swap-in-progress, so
    # it must appear only once the snapshot is complete. Removed on success;
    # its survival after a crash marks the attempt as interrupted.
    (Path(old_dir) / IN_PROGRESS_SENTINEL).write_text("", encoding="utf-8")
    logger.info("Previous data preserved", saved_to=str(old_dir))


def _has_interrupted_attempt(settings: Settings) -> bool:
    old_root = data_dir(settings) / RESTORE_OLD_DIRNAME
    if not old_root.is_dir():
        return False
    return any(
        (attempt / IN_PROGRESS_SENTINEL).is_file()
        for attempt in old_root.iterdir()
        if attempt.is_dir()
    )


def _rollback_interrupted_attempt(settings: Settings) -> None:
    """Roll back the newest interrupted attempt and discard its snapshot."""
    old_root = data_dir(settings) / RESTORE_OLD_DIRNAME
    attempts = sorted(
        (
            d
            for d in old_root.iterdir()
            if d.is_dir() and (d / IN_PROGRESS_SENTINEL).is_file()
        ),
        reverse=True,
    )
    if not attempts:
        return
    latest = attempts[0]
    _rollback_old_data(settings, database_path(settings), latest)
    shutil.rmtree(latest, ignore_errors=True)


def _rollback_old_data(settings: Settings, db_path: Path, old_dir: Path) -> None:
    """Move preserved data back to its original locations."""
    saved_db = Path(old_dir) / "data.db"
    if saved_db.exists():
        for suffix in ("", "-wal", "-shm"):
            saved = Path(str(saved_db) + suffix)
            target = Path(str(db_path) + suffix)
            if saved.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target.unlink()
                shutil.move(str(saved), str(target))
    saved_migrations = Path(old_dir) / "migrations"
    if saved_migrations.is_dir():
        dynamic_dir = dynamic_migrations_path(settings)
        if dynamic_dir.exists():
            shutil.rmtree(dynamic_dir)
        dynamic_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(saved_migrations), str(dynamic_dir))
    saved_files = Path(old_dir) / "files"
    if saved_files.is_dir():
        storage = Path(settings.storage_path)
        if storage.exists():
            shutil.rmtree(storage)
        storage.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(saved_files), str(storage))
    logger.info("Previous data restored", source=str(old_dir))


def _cleanup_old_data(settings: Settings, keep_most_recent: bool = False) -> None:
    """Remove preserved data older than ``restore_retain_old_data_hours``."""
    old_root = data_dir(settings) / RESTORE_OLD_DIRNAME
    if not old_root.is_dir():
        return
    retain_hours = settings.restore_retain_old_data_hours
    cutoff = datetime.now(UTC).timestamp() - retain_hours * 3600
    attempts = sorted(
        (d for d in old_root.iterdir() if d.is_dir()), key=lambda d: d.name
    )
    for index, attempt in enumerate(attempts):
        if keep_most_recent and index == len(attempts) - 1:
            continue
        try:
            mtime = attempt.stat().st_mtime
        except OSError:  # pragma: no cover
            continue
        if mtime < cutoff:
            shutil.rmtree(attempt, ignore_errors=True)
            logger.info(
                "Removed old pre-restore data",
                path=str(attempt),
                retain_hours=retain_hours,
            )


def _sweep_restore_tmp(settings: Settings) -> None:
    """Remove stale scratch archives from ``.restore_tmp``.

    Every validation and restore fetches a copy of the archive there; a
    crash between fetch and cleanup would otherwise leak it forever.
    """
    tmp_dir = data_dir(settings) / RESTORE_TMP_DIRNAME
    if not tmp_dir.is_dir():
        return
    for candidate in tmp_dir.iterdir():
        try:
            if candidate.is_file():
                candidate.unlink()
            elif candidate.is_dir():
                shutil.rmtree(candidate, ignore_errors=True)
        except OSError:  # pragma: no cover - best-effort
            pass


AUDIT_PENDING_FILENAME = ".restore-audit-pending.json"


def mark_audit_pending(settings: Settings, event: str, archive_name: str) -> None:
    """Flag that a restore audit entry is owed once the database is available.

    The entry must land in the database the boot settles on, which does not
    exist until the boot that follows the swap; the flag survives until then.
    """
    path = data_dir(settings) / AUDIT_PENDING_FILENAME
    payload = {"event": event, "archive_name": archive_name}
    path.write_text(json.dumps(payload), encoding="utf-8")


def pop_audit_pending(settings: Settings) -> dict[str, str] | None:
    """Read and clear the audit-pending flag, if present."""
    path = data_dir(settings) / AUDIT_PENDING_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    finally:
        try:
            path.unlink()
        except OSError:  # pragma: no cover - best-effort
            pass
    if not isinstance(payload, dict):
        return None
    return {"event": str(payload.get("event", "")), "archive_name": str(payload.get("archive_name", ""))}
