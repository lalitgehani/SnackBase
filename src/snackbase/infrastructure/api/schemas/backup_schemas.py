"""Pydantic schemas for backup management API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

#: Caller-supplied archive names. Deliberately excludes ``@`` — that
#: character is reserved for the automatic-backup retention prefix, so a
#: manually created name can never collide with it.
ARCHIVE_NAME_PATTERN = r"^[a-z0-9_-]{1,150}\.zip$"


def validate_backup_name(name: str) -> None:
    """Validate a caller-supplied archive name.

    Raises:
        ValueError: When the name does not match the manual-name pattern.
    """
    import re

    if not re.fullmatch(ARCHIVE_NAME_PATTERN, name):
        raise ValueError(
            "name must match ^[a-z0-9_-]{1,150}\\.zip$ — lowercase letters, "
            "digits, hyphen, and underscore only"
        )


class BackupCreateRequest(BaseModel):
    """Request body for creating a backup.

    ``name`` is optional. ``type`` selects the archive kind explicitly; the
    engine routes automatically when omitted (SQLite produces
    ``sqlite_physical``, PostgreSQL produces ``logical``).
    """

    name: str | None = None
    type: str | None = None


class BackupEntryResponse(BaseModel):
    """One archive at the destination.

    ``restorable`` is False for every logical archive: they are portable
    exports, not restore artifacts in this release.
    """

    name: str
    size: int
    modified: datetime
    is_automatic: bool
    backup_type: str = "sqlite_physical"
    restorable: bool = True


class BackupListResponse(BaseModel):
    """All archives plus the in-flight operation, if any.

    ``consecutive_failures`` and ``last_error`` surface the health of the
    automatic-backup schedule so the UI can flag a failing schedule without
    waiting for the alert email.
    """

    backups: list[BackupEntryResponse]
    active: dict[str, Any] | None = None
    consecutive_failures: int = 0
    last_error: str | None = None


class BackupCreatedResponse(BaseModel):
    """Acknowledgement for an accepted backup creation."""

    name: str
    status: str = "started"


class RestoreRequest(BaseModel):
    """Request body for restoring an archive.

    ``force`` proceeds despite warning-severity compatibility issues;
    blocking issues are never overridable.
    """

    force: bool = False


class RestoreStatusResponse(BaseModel):
    """The outcome of the last restore, read from ``.restore-last.json``."""

    archive_name: str
    status: str
    completed_at: str
    error: str | None = None
