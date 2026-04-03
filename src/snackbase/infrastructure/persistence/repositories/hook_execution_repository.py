"""Repository for hook execution log CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.hook_execution import HookExecutionModel


class HookExecutionRepository:
    """Database access layer for the hook_executions table.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, execution: HookExecutionModel) -> HookExecutionModel:
        """Persist a new execution record."""
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def list_for_hook(
        self,
        hook_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[HookExecutionModel], int]:
        """Return paginated execution history for a hook, newest first.

        Args:
            hook_id: Hook primary key.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            Tuple of (executions, total_count).
        """
        query = (
            select(HookExecutionModel)
            .where(HookExecutionModel.hook_id == hook_id)
            .order_by(HookExecutionModel.executed_at.desc())
        )
        result = await self._session.execute(query)
        all_execs = list(result.scalars().all())
        total = len(all_execs)
        return all_execs[offset : offset + limit], total
