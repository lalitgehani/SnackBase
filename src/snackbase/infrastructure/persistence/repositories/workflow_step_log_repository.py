"""Repository for workflow step execution logs (F8.3)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.workflow_step_log import WorkflowStepLogModel


class WorkflowStepLogRepository:
    """Write + read repository for WorkflowStepLogModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: WorkflowStepLogModel) -> WorkflowStepLogModel:
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_for_instance(
        self,
        instance_id: str,
        *,
        offset: int = 0,
        limit: int = 200,
    ) -> tuple[list[WorkflowStepLogModel], int]:
        base = select(WorkflowStepLogModel).where(
            WorkflowStepLogModel.instance_id == instance_id
        )

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        items_q = (
            base.order_by(WorkflowStepLogModel.started_at.asc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self._session.execute(items_q)).scalars().all())
        return items, total
