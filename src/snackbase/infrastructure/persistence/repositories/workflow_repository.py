"""Repository for workflow definitions (F8.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.workflow import WorkflowModel


class WorkflowRepository:
    """CRUD repository for WorkflowModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workflow: WorkflowModel) -> WorkflowModel:
        self._session.add(workflow)
        await self._session.flush()
        return workflow

    async def get(self, workflow_id: str) -> WorkflowModel | None:
        result = await self._session.execute(
            select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_by_webhook_token(self, token: str) -> WorkflowModel | None:
        """Find an enabled webhook-triggered workflow by its token."""
        result = await self._session.execute(
            select(WorkflowModel).where(
                WorkflowModel.trigger_type == "webhook",
                WorkflowModel.enabled.is_(True),
            )
        )
        workflows = result.scalars().all()
        # Token is stored inside the JSON trigger_config; filter in Python
        # for cross-DB compatibility (avoids dialect-specific JSON operators).
        for wf in workflows:
            cfg = wf.trigger_config or {}
            if isinstance(cfg, dict) and cfg.get("token") == token:
                return wf
        return None

    async def list_for_account(
        self,
        account_id: str,
        *,
        trigger_type: str | None = None,
        enabled: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WorkflowModel], int]:
        base = select(WorkflowModel).where(WorkflowModel.account_id == account_id)
        if trigger_type is not None:
            base = base.where(WorkflowModel.trigger_type == trigger_type)
        if enabled is not None:
            base = base.where(WorkflowModel.enabled == enabled)

        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        items_q = base.order_by(WorkflowModel.created_at.desc()).offset(offset).limit(limit)
        items_result = await self._session.execute(items_q)
        items = list(items_result.scalars().all())
        return items, total

    async def list_event_workflows_for_account(
        self,
        account_id: str,
        event_name: str,
        collection: str | None = None,
    ) -> list[WorkflowModel]:
        """Return enabled event-triggered workflows matching event_name + optional collection."""
        result = await self._session.execute(
            select(WorkflowModel).where(
                WorkflowModel.account_id == account_id,
                WorkflowModel.trigger_type == "event",
                WorkflowModel.enabled.is_(True),
            )
        )
        workflows = result.scalars().all()

        matched = []
        for wf in workflows:
            cfg = wf.trigger_config or {}
            if not isinstance(cfg, dict):
                continue
            if cfg.get("event") != event_name:
                continue
            cfg_collection = cfg.get("collection")
            if cfg_collection and collection and cfg_collection != collection:
                continue
            matched.append(wf)
        return matched

    async def list_schedule_workflows(self) -> list[WorkflowModel]:
        """Return all enabled schedule-triggered workflows (across all accounts)."""
        result = await self._session.execute(
            select(WorkflowModel).where(
                WorkflowModel.trigger_type == "schedule",
                WorkflowModel.enabled.is_(True),
            )
        )
        return list(result.scalars().all())

    async def count_for_account(self, account_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).where(WorkflowModel.account_id == account_id)
        )
        return result.scalar_one()

    async def update(self, workflow: WorkflowModel) -> WorkflowModel:
        await self._session.flush()
        return workflow

    async def delete(self, workflow_id: str) -> None:
        wf = await self.get(workflow_id)
        if wf is not None:
            await self._session.delete(wf)
            await self._session.flush()
