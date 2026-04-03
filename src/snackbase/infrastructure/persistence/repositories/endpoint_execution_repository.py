"""Repository for endpoint execution log CRUD operations (F8.2)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.endpoint_execution import EndpointExecutionModel


class EndpointExecutionRepository:
    """Database access layer for the endpoint_executions table.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, execution: EndpointExecutionModel) -> EndpointExecutionModel:
        """Persist a new execution record."""
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def list_for_endpoint(
        self,
        endpoint_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EndpointExecutionModel], int]:
        """Return execution history for an endpoint, newest first.

        Args:
            endpoint_id: Parent endpoint ID.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            Tuple of (executions, total_count).
        """
        base = select(EndpointExecutionModel).where(
            EndpointExecutionModel.endpoint_id == endpoint_id
        )

        count_result = await self._session.execute(
            select(EndpointExecutionModel.id).where(
                EndpointExecutionModel.endpoint_id == endpoint_id
            )
        )
        total = len(count_result.all())

        result = await self._session.execute(
            base.order_by(EndpointExecutionModel.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
