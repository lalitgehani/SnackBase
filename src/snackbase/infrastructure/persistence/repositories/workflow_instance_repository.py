"""Repository for workflow instances (F8.3)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.workflow_instance import WorkflowInstanceModel


class WorkflowInstanceRepository:
    """CRUD repository for WorkflowInstanceModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, instance: WorkflowInstanceModel) -> WorkflowInstanceModel:
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get(self, instance_id: str) -> WorkflowInstanceModel | None:
        result = await self._session.execute(
            select(WorkflowInstanceModel).where(WorkflowInstanceModel.id == instance_id)
        )
        return result.scalar_one_or_none()

    async def list_for_workflow(
        self,
        workflow_id: str,
        account_id: str,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WorkflowInstanceModel], int]:
        base = select(WorkflowInstanceModel).where(
            WorkflowInstanceModel.workflow_id == workflow_id,
            WorkflowInstanceModel.account_id == account_id,
        )
        if status is not None:
            base = base.where(WorkflowInstanceModel.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        items_q = (
            base.order_by(WorkflowInstanceModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self._session.execute(items_q)).scalars().all())
        return items, total

    async def update(self, instance: WorkflowInstanceModel) -> WorkflowInstanceModel:
        await self._session.flush()
        return instance

    async def delete(self, instance_id: str) -> None:
        inst = await self.get(instance_id)
        if inst is not None:
            await self._session.delete(inst)
            await self._session.flush()
