"""Audit trail for backup operations.

Backup events are appended straight to the immutable audit log through the
existing audit repository — never routed through the ``jobs`` table. Actors
are user identities for API-triggered operations and ``system`` for CLI and
scheduled runs.

Events map onto the audit log's ``operation`` vocabulary:
``CREATE`` for archive creation, ``DELETE`` for archive deletion, and
``UPDATE`` for restore lifecycle events.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.backup.destinations import BackupError
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)

SYSTEM_ACTOR_ID = "system"
SYSTEM_ACTOR_EMAIL = "system@snackbase.internal"
SYSTEM_ACTOR_NAME = "system"
AUDIT_TABLE_NAME = "backup"
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

EVENT_CREATE_STARTED = "backup.create.started"
EVENT_CREATE_COMPLETED = "backup.create.completed"
EVENT_CREATE_FAILED = "backup.create.failed"
EVENT_DELETE = "backup.delete"
EVENT_RESTORE_REQUESTED = "backup.restore.requested"
EVENT_RESTORE_COMPLETED = "backup.restore.completed"
EVENT_RESTORE_FAILED = "backup.restore.failed"
EVENT_RETENTION_PRUNED = "backup.retention.pruned"

_OPERATION_BY_EVENT = {
    EVENT_CREATE_STARTED: "CREATE",
    EVENT_CREATE_COMPLETED: "CREATE",
    EVENT_CREATE_FAILED: "CREATE",
    EVENT_DELETE: "DELETE",
    EVENT_RESTORE_REQUESTED: "UPDATE",
    EVENT_RESTORE_COMPLETED: "UPDATE",
    EVENT_RESTORE_FAILED: "UPDATE",
    EVENT_RETENTION_PRUNED: "DELETE",
}


async def write_backup_event(
    session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]],
    *,
    event: str,
    name: str,
    destination_type: str,
    size: int | None = None,
    actor_user_id: str = SYSTEM_ACTOR_ID,
    actor_email: str = SYSTEM_ACTOR_EMAIL,
    actor_name: str = SYSTEM_ACTOR_NAME,
    account_id: str = SYSTEM_ACCOUNT_ID,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append one backup audit entry in its own committed transaction.

    Audit writes are permitted during a backup and must never fail the
    operation they describe... with one deliberate exception: a total
    failure of the audit path surfaces as a :class:`BackupError` so a
    deployment with a broken audit log cannot silently take unaudited
    backups.
    """
    metadata: dict[str, Any] = {
        "event": event,
        "destination": destination_type,
        "actor": actor_user_id,
    }
    if size is not None:
        metadata["size"] = size
    if extra:
        metadata.update(extra)

    async with session_factory() as session:
        try:
            await AuditLogRepository(session).create(
                AuditLogModel(
                    account_id=account_id,
                    operation=_OPERATION_BY_EVENT[event],
                    table_name=AUDIT_TABLE_NAME,
                    record_id=name,
                    column_name="event",
                    old_value=None,
                    new_value=event,
                    user_id=actor_user_id,
                    user_email=actor_email,
                    user_name=actor_name,
                    occurred_at=datetime.now(UTC),
                    extra_metadata=metadata,
                )
            )
            await session.commit()
        except BackupError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"Failed to write backup audit entry: {exc}") from exc
