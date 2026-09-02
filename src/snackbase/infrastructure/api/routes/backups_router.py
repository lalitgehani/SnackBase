"""Admin API routes for backup management.

All endpoints require superadmin access. Provides:

- POST /       — create a backup (202; runs in the background)
- GET /        — list archives and the in-flight operation, if any
- DELETE /{name} — delete an archive (204)
- GET /{name}/download — stream an archive to the caller
- POST /upload — store an archive taken elsewhere at the destination

Notes:
- In-flight state comes from the lock file (F2.2), never from the database.
- ``/upload`` is exempt from ``settings.max_file_size``: archives are
  legitimately large. It streams to a staging file and validates the zip
  and its manifest before the destination handoff.
- Literal path segments (``upload``) are declared before the ``{name}``
  routes so FastAPI cannot match them as archive names.
"""

import asyncio
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser, get_db_session
from snackbase.infrastructure.api.schemas.backup_schemas import (
    ARCHIVE_NAME_PATTERN,
    BackupCreatedResponse,
    BackupCreateRequest,
    BackupEntryResponse,
    BackupListResponse,
    RestoreRequest,
    RestoreStatusResponse,
    validate_backup_name,
)
from snackbase.infrastructure.backup.archive import MANIFEST_MEMBER, member_names
from snackbase.infrastructure.backup.audit import (
    EVENT_RESTORE_REQUESTED,
    write_backup_event,
)
from snackbase.infrastructure.backup.destinations import (
    BackupInProgressError,
    BackupNotFoundError,
    resolve_destination,
)
from snackbase.infrastructure.backup.lock import active_operation, backup_lock
from snackbase.infrastructure.backup.manifest import BackupManifest
from snackbase.infrastructure.backup.restart import schedule_restart
from snackbase.infrastructure.backup.restore import (
    RestoreAbortedError,
    check_engine_is_sqlite,
    destination_to_marker_dict,
    read_last_restore,
    validate_restore_candidate,
    write_marker,
)
from snackbase.infrastructure.backup.service import (
    backup_working_dir,
    create_backup,
    generate_backup_name,
    staging_dir,
)
from snackbase.infrastructure.persistence.database import get_db_manager

router = APIRouter(tags=["backups"])

logger = get_logger(__name__)

# Keeps references to in-flight tasks so they are not garbage-collected
# mid-backup (asyncio only holds weak references to running tasks).
_running_tasks: set[asyncio.Task[None]] = set()


def _invalid_name_detail() -> str:
    return (
        "name must match ^[a-z0-9_-]{1,150}\\.zip$ — lowercase letters, digits, "
        "hyphen, and underscore only"
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_backup(
    _: SuperadminUser,
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Store an uploaded archive at the configured destination.

    The name is validated against the manual-name pattern, the payload is
    streamed to a staging file (never buffered in memory), and the archive
    must open as a zip carrying a parsable ``manifest.json`` before it is
    committed to the destination.
    """
    destination = await resolve_destination(session)
    name = file.filename or ""
    if not re.fullmatch(ARCHIVE_NAME_PATTERN, name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_invalid_name_detail(),
        )
    if await destination.exists(name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Archive already exists: {name}",
        )

    working_dir = backup_working_dir(destination)
    staging = staging_dir(working_dir)
    staging.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed below
        dir=staging, prefix="upload_", suffix=".zip", delete=False
    )
    temp_path = Path(handle.name)
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
        handle.close()

        try:
            names = member_names(temp_path)
            if MANIFEST_MEMBER not in names:
                raise ValueError(f"Archive is missing {MANIFEST_MEMBER}")
            with zipfile.ZipFile(temp_path) as archive:
                payload = archive.read(MANIFEST_MEMBER)
            BackupManifest.from_json(payload.decode("utf-8"))
        except (zipfile.BadZipFile, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not a valid backup archive: {exc}",
            ) from exc

        await destination.write(name, temp_path)
    finally:
        if not handle.closed:
            handle.close()
        temp_path.unlink(missing_ok=True)

    logger.info("Backup archive uploaded", archive=name)
    return {"name": name, "status": "uploaded"}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_backup_endpoint(
    user: SuperadminUser,
    request: BackupCreateRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> BackupCreatedResponse:
    """Start creating a backup archive; returns 202 immediately.

    The archive is built in a background task. A second operation while one
    is in flight is answered with 409 naming the in-flight operation.
    """
    name = (request.name if request else None) or generate_backup_name()
    if request is not None and request.name is not None:
        try:
            validate_backup_name(request.name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
    destination = await resolve_destination(session)
    working_dir = backup_working_dir(destination)

    current = active_operation(working_dir)
    if current is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A backup or restore is already in progress",
                "active": current,
            },
        )
    if await destination.exists(name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Archive already exists: {name}",
        )

    session_factory = get_db_manager().session
    actor = (user.id, user.email, user.email)

    async def _run() -> None:
        try:
            await create_backup(
                name=name,
                destination=destination,
                session_factory=session_factory,
                actor=actor,
            )
        except Exception as exc:  # noqa: BLE001 - background task boundary
            logger.error("Background backup failed", archive=name, error=str(exc))

    task = asyncio.create_task(_run(), name=f"backup-{name}")
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    logger.info("Backup requested", archive=name, requested_by=user.id)
    return BackupCreatedResponse(name=name)


@router.get("", response_model=BackupListResponse)
async def list_backups(
    _: SuperadminUser,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> BackupListResponse:
    """List every archive at the destination, newest first, plus in-flight state."""
    destination = await resolve_destination(session)
    entries = await destination.list()
    working_dir = backup_working_dir(destination)
    scheduler = getattr(request.app.state, "backup_scheduler", None)
    failures = getattr(getattr(scheduler, "alerts", None), "consecutive_failures", 0)
    last_error = getattr(getattr(scheduler, "alerts", None), "last_error", None)
    return BackupListResponse(
        backups=[
            BackupEntryResponse(
                name=entry.name,
                size=entry.size,
                modified=entry.modified,
                is_automatic=entry.name.startswith("@auto_"),
            )
            for entry in entries
        ],
        active=active_operation(working_dir),
        consecutive_failures=int(failures or 0),
        last_error=last_error,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    name: str,
    _: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an archive from the destination."""
    if not re.fullmatch(ARCHIVE_NAME_PATTERN, name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive name",
        )
    destination = await resolve_destination(session)
    working_dir = backup_working_dir(destination)
    current = active_operation(working_dir)
    if current is not None and current.get("name") == name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archive is currently being written",
        )
    try:
        await destination.delete(name)
    except BackupNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    logger.info("Backup archive deleted", archive=name)


@router.get("/{name}/download")
async def download_backup(
    name: str,
    _: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream an archive with ``Content-Disposition: attachment``.

    The archive is streamed in chunks from the destination — for S3, the
    object body is streamed directly rather than downloaded to a temp file.
    """
    if not re.fullmatch(ARCHIVE_NAME_PATTERN, name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive name",
        )
    destination = await resolve_destination(session)
    try:
        stream = destination.open_download_stream(name)
    except BackupNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return StreamingResponse(
        stream,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/restore-status", response_model=RestoreStatusResponse)
async def get_restore_status(
    _: SuperadminUser,
) -> RestoreStatusResponse:
    """Report the outcome of the last restore (F3.3).

    Read from ``<data_dir>/.restore-last.json``, which the pre-boot executor
    writes on both success and failure. Returns 404 when no restore has
    been performed on this instance.
    """
    from snackbase.core.config import get_settings

    result = read_last_restore(get_settings())
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No restore has been performed on this instance",
        )
    return RestoreStatusResponse(
        archive_name=result.archive_name,
        status=result.status,
        completed_at=result.completed_at,
        error=result.error,
    )


@router.post("/{name}/restore", status_code=status.HTTP_202_ACCEPTED)
async def restore_backup(
    name: str,
    user: SuperadminUser,
    request: RestoreRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Request a restore; the swap happens before the next boot opens the DB.

    The full validation sequence runs before anything is written. On
    success a marker file is written beside the database, the instance
    schedules its own graceful shutdown, and the supervisor restarts it —
    the pre-boot executor then performs the swap before any database
    connection is opened.
    """
    from snackbase.core.config import get_settings
    from snackbase.infrastructure.backup.manifest import fingerprints_from_settings

    settings = get_settings()
    force = bool(request.force) if request is not None else False
    destination = await resolve_destination(session)
    working_dir = backup_working_dir(destination)

    try:
        async with backup_lock(name, "restore", working_dir):
            try:
                validation = validate_restore_candidate(destination, name, settings)
            except BackupNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
                ) from exc
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                ) from exc

            try:
                check_engine_is_sqlite(settings)
            except RestoreAbortedError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                ) from exc

            if validation.blocking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Archive has blocking compatibility issues; "
                        "restore refused",
                        "issues": [
                            {"type": i.type, "severity": i.severity, "message": i.message}
                            for i in validation.blocking
                        ],
                    },
                )
            if validation.warnings and not force:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": (
                            "Archive has compatibility warnings; "
                            "resend with force=true to proceed"
                        ),
                        "issues": [
                            {"type": i.type, "severity": i.severity, "message": i.message}
                            for i in validation.warnings
                        ],
                    },
                )

            marker = write_marker(
                settings,
                archive_name=name,
                destination=destination_to_marker_dict(destination, settings),
                requested_by=user.id,
                manifest_fingerprints=fingerprints_from_settings(settings),
            )
    except BackupInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A backup or restore is already in progress",
                "active": {"operation": exc.operation, "name": exc.name},
            },
        ) from exc

    # Audit before exiting; the entry lands in the current (pre-restore) DB.
    session_factory = get_db_manager().session
    try:
        await write_backup_event(
            session_factory,
            event=EVENT_RESTORE_REQUESTED,
            name=name,
            destination_type="",
            actor_user_id=user.id,
            actor_email=user.email,
            actor_name=user.email,
            account_id=user.account_id,
        )
    except Exception as exc:  # noqa: BLE001 - must not block the restart
        logger.error("Failed to write restore audit entry", error=str(exc))

    schedule_restart()

    return marker
