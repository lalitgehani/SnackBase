"""Execution log retention purge for Functions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.repositories.function_repository import (
    FunctionRepository,
)

logger = get_logger(__name__)


async def purge_old_function_executions(session: AsyncSession) -> int:
    """Delete function_executions older than configured retention days."""
    settings = get_settings()
    days = max(1, settings.function_execution_retention_days)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    repo = FunctionRepository(session)
    deleted = await repo.purge_executions_before(cutoff)
    await session.commit()
    logger.info("Purged function executions", deleted=deleted, cutoff=cutoff.isoformat())
    return deleted
