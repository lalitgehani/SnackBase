"""Repository for custom endpoint CRUD operations (F8.2)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.endpoint import EndpointModel


class EndpointRepository:
    """Database access layer for the endpoints table.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, endpoint: EndpointModel) -> EndpointModel:
        """Persist a new endpoint record."""
        self._session.add(endpoint)
        await self._session.flush()
        return endpoint

    async def get(self, endpoint_id: str) -> EndpointModel | None:
        """Retrieve an endpoint by primary key."""
        result = await self._session.execute(
            select(EndpointModel).where(EndpointModel.id == endpoint_id)
        )
        return result.scalar_one_or_none()

    async def get_by_path_and_method(
        self,
        account_id: str,
        method: str,
    ) -> list[EndpointModel]:
        """Return all enabled endpoints for an account and HTTP method.

        The caller is responsible for matching path templates (including
        parameterised segments) against the actual request path.

        Args:
            account_id: Tenant account ID.
            method: HTTP method (uppercased).

        Returns:
            List of enabled EndpointModel instances for this method.
        """
        result = await self._session.execute(
            select(EndpointModel).where(
                EndpointModel.account_id == account_id,
                EndpointModel.method == method.upper(),
                EndpointModel.enabled == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_all_enabled_for_account(self, account_id: str) -> list[EndpointModel]:
        """Return all enabled endpoints for an account (any method).

        Used by the dispatcher to find a matching endpoint for a request.

        Args:
            account_id: Tenant account ID.

        Returns:
            List of enabled EndpointModel instances.
        """
        result = await self._session.execute(
            select(EndpointModel).where(
                EndpointModel.account_id == account_id,
                EndpointModel.enabled == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def list_for_account(
        self,
        account_id: str,
        *,
        method: str | None = None,
        enabled: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EndpointModel], int]:
        """List endpoints for an account with optional filtering and pagination.

        Args:
            account_id: Tenant account ID.
            method: Filter by HTTP method (case-insensitive).
            enabled: If not None, filter by enabled status.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            Tuple of (endpoints, total_count).
        """
        query = select(EndpointModel).where(EndpointModel.account_id == account_id)

        if enabled is not None:
            query = query.where(EndpointModel.enabled == enabled)
        if method is not None:
            query = query.where(EndpointModel.method == method.upper())

        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            query.order_by(EndpointModel.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def update(self, endpoint: EndpointModel) -> EndpointModel:
        """Persist changes to an existing endpoint."""
        await self._session.flush()
        return endpoint

    async def delete(self, endpoint_id: str) -> None:
        """Delete an endpoint by primary key."""
        endpoint = await self.get(endpoint_id)
        if endpoint:
            await self._session.delete(endpoint)
            await self._session.flush()

    # ------------------------------------------------------------------
    # Limit enforcement
    # ------------------------------------------------------------------

    async def count_for_account(self, account_id: str) -> int:
        """Count all endpoints for an account.

        Used for limit enforcement (max N per account).

        Args:
            account_id: Tenant account ID.

        Returns:
            Total number of endpoints for the account.
        """
        result = await self._session.execute(
            select(func.count(EndpointModel.id)).where(
                EndpointModel.account_id == account_id
            )
        )
        return result.scalar_one()

    async def exists_by_path_and_method(
        self,
        account_id: str,
        path: str,
        method: str,
        exclude_id: str | None = None,
    ) -> bool:
        """Check if an endpoint with the same (account_id, path, method) exists.

        Args:
            account_id: Tenant account ID.
            path: URL path template.
            method: HTTP method (uppercased internally).
            exclude_id: ID to exclude from the check (for updates).

        Returns:
            True if a conflicting endpoint exists.
        """
        query = select(EndpointModel.id).where(
            EndpointModel.account_id == account_id,
            EndpointModel.path == path,
            EndpointModel.method == method.upper(),
        )
        if exclude_id:
            query = query.where(EndpointModel.id != exclude_id)

        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None
