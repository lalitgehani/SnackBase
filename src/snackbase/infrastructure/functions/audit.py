"""Best-effort audit emission for function lifecycle events.

Never stores secret values, ciphertext, or credentials in audit metadata.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


async def emit_function_audit(
    session: AsyncSession,
    *,
    account_id: str,
    actor_id: str | None,
    operation: str,
    function_id: str | None,
    details: dict[str, Any] | None = None,
    actor_email: str | None = None,
) -> None:
    """Write an immutable audit_log row for a function management event.

    Failures are logged and swallowed so management APIs are not blocked.
    Uses a nested transaction so a failed audit write cannot poison the
    caller's session.
    """
    try:
        from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
        from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        safe_details = dict(details or {})
        for key in list(safe_details.keys()):
            lowered = key.lower()
            if any(t in lowered for t in ("secret", "token", "password", "ciphertext")):
                safe_details[key] = "[redacted]"

        op = operation[:10].upper()
        entry = AuditLogModel(
            account_id=account_id,
            operation=op if op in {"CREATE", "UPDATE", "DELETE"} else "UPDATE",
            table_name="functions",
            record_id=function_id or "unknown",
            column_name=operation[:255],
            old_value=None,
            new_value=None,
            user_id=actor_id or "system",
            user_email=actor_email or "system@snackbase.local",
            user_name=actor_email or actor_id or "system",
            extra_metadata={"event": operation, **safe_details},
        )
        async with session.begin_nested():
            repo = AuditLogRepository(session)
            await repo.create(entry)
    except Exception:
        logger.debug("function audit emit skipped", operation=operation, exc_info=True)
