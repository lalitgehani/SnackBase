"""Repository for Functions CRUD and related version/execution/secret access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.function import (
    FunctionExecutionModel,
    FunctionModel,
    FunctionSecretModel,
    FunctionVersionModel,
)


class FunctionRepository:
    """Database access layer for functions and related tables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    async def create(self, function: FunctionModel) -> FunctionModel:
        self._session.add(function)
        await self._session.flush()
        return function

    async def get(self, function_id: str) -> FunctionModel | None:
        result = await self._session.execute(
            select(FunctionModel).where(FunctionModel.id == function_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        account_id: str,
        slug: str,
        *,
        include_removed: bool = False,
    ) -> FunctionModel | None:
        query = select(FunctionModel).where(
            FunctionModel.account_id == account_id,
            FunctionModel.slug == slug,
        )
        if not include_removed:
            query = query.where(FunctionModel.status != "REMOVED")
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_account(
        self,
        account_id: str,
        *,
        enabled: bool | None = None,
        include_removed: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[FunctionModel], int]:
        query = select(FunctionModel).where(FunctionModel.account_id == account_id)
        if not include_removed:
            query = query.where(FunctionModel.status != "REMOVED")
        if enabled is not None:
            query = query.where(FunctionModel.enabled == enabled)

        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        result = await self._session.execute(
            query.order_by(FunctionModel.updated_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def update(self, function: FunctionModel) -> FunctionModel:
        function.updated_at = datetime.now(UTC)
        await self._session.flush()
        return function

    async def soft_delete(self, function: FunctionModel) -> FunctionModel:
        function.status = "REMOVED"
        function.enabled = False
        function.updated_at = datetime.now(UTC)
        await self._session.flush()
        return function

    async def count_for_account(self, account_id: str, *, include_removed: bool = False) -> int:
        query = select(func.count(FunctionModel.id)).where(
            FunctionModel.account_id == account_id
        )
        if not include_removed:
            query = query.where(FunctionModel.status != "REMOVED")
        result = await self._session.execute(query)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------------

    async def create_version(self, version: FunctionVersionModel) -> FunctionVersionModel:
        self._session.add(version)
        await self._session.flush()
        return version

    async def get_version(self, version_id: str) -> FunctionVersionModel | None:
        result = await self._session.execute(
            select(FunctionVersionModel).where(FunctionVersionModel.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        function_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[FunctionVersionModel], int]:
        query = select(FunctionVersionModel).where(
            FunctionVersionModel.function_id == function_id
        )
        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        result = await self._session.execute(
            query.order_by(FunctionVersionModel.version.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def next_version_number(self, function_id: str) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(FunctionVersionModel.version), 0)).where(
                FunctionVersionModel.function_id == function_id
            )
        )
        return int(result.scalar_one()) + 1

    async def set_active_version(self, function: FunctionModel, version_id: str) -> FunctionModel:
        function.active_version_id = version_id
        function.updated_at = datetime.now(UTC)
        await self._session.flush()
        return function

    async def list_old_versions(
        self,
        function_id: str,
        keep: int,
    ) -> list[FunctionVersionModel]:
        """Return versions older than the newest `keep` versions."""
        result = await self._session.execute(
            select(FunctionVersionModel)
            .where(FunctionVersionModel.function_id == function_id)
            .order_by(FunctionVersionModel.version.desc())
            .offset(keep)
        )
        return list(result.scalars().all())

    async def delete_version(self, version: FunctionVersionModel) -> None:
        await self._session.delete(version)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Executions
    # ------------------------------------------------------------------

    async def create_execution(
        self, execution: FunctionExecutionModel
    ) -> FunctionExecutionModel:
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def list_executions(
        self,
        function_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[FunctionExecutionModel], int]:
        query = select(FunctionExecutionModel).where(
            FunctionExecutionModel.function_id == function_id
        )
        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        result = await self._session.execute(
            query.order_by(FunctionExecutionModel.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_execution(self, execution_id: str) -> FunctionExecutionModel | None:
        result = await self._session.execute(
            select(FunctionExecutionModel).where(FunctionExecutionModel.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def execution_stats(
        self,
        function_id: str,
        *,
        since: datetime,
    ) -> dict[str, Any]:
        """Aggregate execution counts and duration percentiles since `since`."""
        result = await self._session.execute(
            select(FunctionExecutionModel).where(
                FunctionExecutionModel.function_id == function_id,
                FunctionExecutionModel.executed_at >= since,
            )
        )
        rows = list(result.scalars().all())
        by_status: dict[str, int] = {"success": 0, "failed": 0, "timeout": 0}
        durations: list[int] = []
        for row in rows:
            by_status[row.status] = by_status.get(row.status, 0) + 1
            if row.duration_ms is not None:
                durations.append(row.duration_ms)
        durations.sort()
        n = len(durations)

        def _pct(p: float) -> int | None:
            if n == 0:
                return None
            idx = min(n - 1, max(0, int(round(p * (n - 1)))))
            return durations[idx]

        return {
            "total": len(rows),
            "by_status": by_status,
            "p50_ms": _pct(0.50),
            "p95_ms": _pct(0.95),
        }

    async def purge_executions_before(self, cutoff: datetime) -> int:
        result = await self._session.execute(
            select(FunctionExecutionModel).where(
                FunctionExecutionModel.executed_at < cutoff
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows)

    # ------------------------------------------------------------------
    # Secrets
    # ------------------------------------------------------------------

    async def list_secrets(self, account_id: str) -> list[FunctionSecretModel]:
        result = await self._session.execute(
            select(FunctionSecretModel)
            .where(FunctionSecretModel.account_id == account_id)
            .order_by(FunctionSecretModel.name.asc())
        )
        return list(result.scalars().all())

    async def get_secret(self, account_id: str, name: str) -> FunctionSecretModel | None:
        result = await self._session.execute(
            select(FunctionSecretModel).where(
                FunctionSecretModel.account_id == account_id,
                FunctionSecretModel.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_secret(self, secret: FunctionSecretModel) -> FunctionSecretModel:
        existing = await self.get_secret(secret.account_id, secret.name)
        if existing:
            existing.value_encrypted = secret.value_encrypted
            existing.updated_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        self._session.add(secret)
        await self._session.flush()
        return secret

    async def delete_secret(self, account_id: str, name: str) -> bool:
        secret = await self.get_secret(account_id, name)
        if not secret:
            return False
        await self._session.delete(secret)
        await self._session.flush()
        return True

    async def count_secrets(self, account_id: str) -> int:
        result = await self._session.execute(
            select(func.count(FunctionSecretModel.id)).where(
                FunctionSecretModel.account_id == account_id
            )
        )
        return result.scalar_one()

    async def get_all_secrets_for_inject(
        self, account_id: str
    ) -> list[FunctionSecretModel]:
        return await self.list_secrets(account_id)
