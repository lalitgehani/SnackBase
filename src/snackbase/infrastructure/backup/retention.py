"""Automatic backup retention: prune old ``@auto_`` archives after a run.

Retention operates on the destination listing, not a database index — the
same approach as listing itself. Only archives with the reserved ``@auto_``
prefix are ever deleted; manual and uploaded archives are outside retention
entirely, which is why the manual-name pattern excludes ``@``.
"""

from typing import Any

AUTOMATIC_PREFIX = "@auto_"


def select_for_pruning(
    names: list[str],
    *,
    max_keep: int,
    keep_name: str | None = None,
) -> list[str]:
    """Pick the automatic archives to delete, newest-first input.

    ``names`` must be sorted newest first (as ``BackupDestination.list``
    returns). The archive just created occupies one retention slot and is
    never itself a candidate — even if ``max_keep`` is somehow zero — so the
    total number of automatic archives is capped at ``max_keep``.
    """
    has_new = keep_name is not None and keep_name in names
    slots = max(0, max_keep) - (1 if has_new else 0)
    candidates = [name for name in names if name != keep_name]
    return candidates[slots:]


async def prune_automatic_backups(
    destination: Any,
    *,
    max_keep: int,
    keep_name: str | None = None,
    session_factory: Any = None,
) -> list[str]:
    """Cap the number of automatic archives at ``max_keep``.

    Runs only after the new archive is confirmed written, so a failed
    backup never causes deletion of a good one. A deletion failure is
    logged as a warning and does not fail the backup.
    """
    entries = await destination.list(AUTOMATIC_PREFIX)
    to_delete = select_for_pruning(
        [entry.name for entry in entries],
        max_keep=max_keep,
        keep_name=keep_name,
    )
    deleted: list[str] = []
    for name in to_delete:
        try:
            await destination.delete(name)
            deleted.append(name)
        except Exception as exc:  # noqa: BLE001 - retention is best-effort
            from snackbase.core.logging import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "Retention could not delete archive", archive=name, error=str(exc)
            )

    if deleted and session_factory is not None:
        from snackbase.infrastructure.backup.audit import (
            EVENT_RETENTION_PRUNED,
            write_backup_event,
        )

        try:
            await write_backup_event(
                session_factory,
                event=EVENT_RETENTION_PRUNED,
                name=keep_name or "",
                destination_type="",
                extra={"deleted": deleted},
            )
        except Exception as exc:  # noqa: BLE001 - retention is best-effort
            from snackbase.core.logging import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "Failed to write retention audit entry", error=str(exc)
            )
    return deleted
