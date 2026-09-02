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
    """Request body for creating a backup. ``name`` is optional."""

    name: str | None = None


class BackupEntryResponse(BaseModel):
    """One archive at the destination."""

    name: str
    size: int
    modified: datetime
    is_automatic: bool


class BackupListResponse(BaseModel):
    """All archives plus the in-flight operation, if any."""

    backups: list[BackupEntryResponse]
    active: dict[str, Any] | None = None


class BackupCreatedResponse(BaseModel):
    """Acknowledgement for an accepted backup creation."""

    name: str
    status: str = "started"
