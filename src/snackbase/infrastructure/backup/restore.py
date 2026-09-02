"""Pre-boot restore: the data swap happens before any database connection.

The API (or CLI) validates an archive, writes a marker file beside the
SQLite database, and exits. The supervisor restarts the process; at
startup — before the database engine is created and before migrations run
— the marker is detected and the swap performed. Nothing holds the database
open during the swap because nothing has opened it yet. The marker file is
the transaction record: a crash mid-restore is recovered by retrying on the
next boot rather than by unwinding.
"""

import json
import shutil
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snackbase.core.config import Settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.backup.archive import (
    DATA_MEMBER,
    FILES_PREFIX,
    MANIFEST_MEMBER,
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
)

logger = get_logger(__name__)

MARKER_FILENAME = ".restore-pending.json"
MARKER_INVALID_SUFFIX = ".invalid"
LAST_RESTORE_FILENAME = ".restore-last.json"
RESTORE_OLD_DIRNAME = ".restore_old"
RESTORE_TMP_DIRNAME = ".restore_tmp"
EXTRACT_SUBDIR = "extracted"


class RestoreAbortedError(RuntimeError):
    """Raised when a restore request or a pending restore cannot proceed."""


@dataclass
class RestoreValidation:
    """Structured result of pre-restore compatibility checking."""

    manifest: BackupManifest
    blocking: list[CompatibilityIssue]
    warnings: list[CompatibilityIssue]


@dataclass
class RestoreResult:
    """Outcome of a restore, persisted to ``.restore-last.json``."""

    archive_name: str
    status: str  # "completed" | "failed"
    completed_at: str
    error: str | None = None


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
            endpoint_url=destination.get("endpoint_url") or None,
        )
    raise RestoreAbortedError(f"Unknown destination type in restore marker: {kind!r}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_restore_candidate(
    destination: BackupDestination,
    name: str,
    settings: Settings,
) -> RestoreValidation:
    """Validate an archive for restore without touching any live state.

    Fetches the archive to a scratch location, checks the zip layout and
    manifest, and runs the compatibility check against current settings.

    Raises:
        BackupNotFoundError: The archive does not exist at the destination.
        ValueError: Not a zip, missing ``manifest.json``/``data.db``, or an
            unparsable manifest.
    """
    scratch = data_dir(settings) / RESTORE_TMP_DIRNAME
    scratch.mkdir(parents=True, exist_ok=True)
    local_copy = scratch / f"validate-{uuid.uuid4().hex}.zip"
    try:
        destination.read_sync(name, local_copy)
        manifest = _parse_manifest(local_copy, name)
        issues = manifest.verify_compatibility(settings)
        return RestoreValidation(
            manifest=manifest,
            blocking=[i for i in issues if i.severity == "blocking"],
            warnings=[i for i in issues if i.severity == "warning"],
        )
    finally:
        shutil.rmtree(local_copy, ignore_errors=True)


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
        return RestoreResult(
            archive_name=str(data.get("archive_name", "unknown")),
            status=str(data.get("status", "unknown")),
            completed_at=str(data.get("completed_at", "")),
            error=data.get("error"),
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Boot-time executor
# ---------------------------------------------------------------------------


def execute_pending_restore(settings: Settings) -> RestoreResult | None:
    """Perform the pending restore before anything opens the database.

    Returns None when no marker exists (normal boot; also prunes expired
    ``.restore_old`` data). On success the database and files have been
    replaced, the marker removed, and the previous data preserved under
    ``.restore_old/<timestamp>/``. Any failure through the swap rolls
    everything back, leaves the marker in place, and raises
    :class:`RestoreAbortedError` so the caller aborts boot with a non-zero
    exit.
    """
    marker = read_marker(settings)
    if marker is None:
        _cleanup_old_data(settings)
        return None

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
        except RestoreAbortedError:
            raise
        except Exception as exc:
            raise RestoreAbortedError(
                f"Cannot resolve destination for restore: {exc}"
            ) from exc

        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            destination.read_sync(archive_name, archive_local)
        except BackupNotFoundError as exc:
            raise RestoreAbortedError(
                f"Archive {archive_name} no longer exists at the destination"
            ) from exc

        _check_free_space(working, archive_local)

        names = member_names(archive_local)
        validate_member_paths(names)
        if MANIFEST_MEMBER not in names or DATA_MEMBER not in names:
            raise RestoreAbortedError(
                f"Archive {archive_name} is missing {MANIFEST_MEMBER} or {DATA_MEMBER}"
            )
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_local) as archive:
            archive.extractall(extract_dir)
        logger.info("Archive extracted", archive=archive_name)

        # Re-verify fingerprints: the environment may have changed between
        # request and boot.
        manifest = BackupManifest.from_json(
            (extract_dir / MANIFEST_MEMBER).read_text(encoding="utf-8")
        )
        issues = manifest.verify_compatibility(settings)
        blocking = [issue for issue in issues if issue.severity == "blocking"]
        if blocking:
            raise RestoreAbortedError(
                "Archive fingerprints no longer match this instance: "
                + "; ".join(issue.message for issue in blocking)
            )

        db_path = database_path(settings)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        old_dir = working / RESTORE_OLD_DIRNAME / stamp
        old_dir.mkdir(parents=True, exist_ok=True)
        _preserve_current_data(settings, db_path, old_dir)

        try:
            shutil.move(str(extract_dir / DATA_MEMBER), str(db_path))
            if manifest.includes_files:
                extracted_files = extract_dir / FILES_PREFIX.rstrip("/")
                storage = Path(settings.storage_path)
                if extracted_files.is_dir():
                    if storage.exists():
                        shutil.rmtree(storage)
                    storage.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(extracted_files), str(storage))
            logger.info("Data swap complete", archive=archive_name)
        except Exception as exc:
            # The swap failed: put the old data back and leave the marker so
            # the next boot retries.
            _rollback_old_data(settings, db_path, old_dir)
            raise RestoreAbortedError(f"Data swap failed: {exc}") from exc

        # Success: the marker is the transaction record — remove it.
        marker_path(settings).unlink(missing_ok=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _cleanup_old_data(settings, keep_most_recent=True)
        result = RestoreResult(
            archive_name=archive_name,
            status="completed",
            completed_at=_utc_now_iso(),
        )
        record_last_restore(settings, result)
        mark_audit_pending(settings, "backup.restore.completed", archive_name)
        logger.info("Restore completed", archive=archive_name)
        return result

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


def _check_free_space(working: Path, archive_local: Path) -> None:
    """Warn at and abort below twice the archive size in free disk space."""
    required = archive_local.stat().st_size * 2
    try:
        free = shutil.disk_usage(str(working)).free
    except OSError:  # pragma: no cover - unusual filesystems
        return
    if free < required:
        raise RestoreAbortedError(
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


def _preserve_current_data(settings: Settings, db_path: Path, old_dir: Path) -> None:
    """Move the current database (with -wal/-shm siblings) and files tree aside."""
    for suffix in ("", "-wal", "-shm"):
        sibling = Path(str(db_path) + suffix)
        if sibling.exists():
            shutil.move(str(sibling), str(Path(old_dir) / f"data.db{suffix}"))
    storage = Path(settings.storage_path)
    if storage.is_dir():
        shutil.move(str(storage), str(Path(old_dir) / "files"))
    logger.info("Previous data preserved", saved_to=str(old_dir))


def _has_interrupted_attempt(settings: Settings) -> bool:
    old_root = data_dir(settings) / RESTORE_OLD_DIRNAME
    return old_root.is_dir() and any(old_root.iterdir())


def _rollback_interrupted_attempt(settings: Settings) -> None:
    """Roll back the newest interrupted attempt and discard its snapshot."""
    old_root = data_dir(settings) / RESTORE_OLD_DIRNAME
    attempts = sorted((d for d in old_root.iterdir() if d.is_dir()), reverse=True)
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


AUDIT_PENDING_FILENAME = ".restore-audit-pending.json"


def mark_audit_pending(settings: Settings, event: str, archive_name: str) -> None:
    """Flag that a restore audit entry is owed once the database is available.

    The entry must land in the restored database, which does not exist
    until the boot that follows the swap; the flag survives until then.
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
