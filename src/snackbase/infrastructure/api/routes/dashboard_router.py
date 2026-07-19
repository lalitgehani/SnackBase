"""Dashboard API routes.

Provides endpoints for dashboard statistics and metrics.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services import DashboardService
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import DashboardStats
from snackbase.infrastructure.persistence.database import get_db_session

router = APIRouter()

@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    response_model=DashboardStats,
    responses={
        403: {"description": "Superadmin access required"},
        422: {"description": "Invalid range parameter"},
    },
)
async def get_dashboard_stats(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
    range: Annotated[
        Literal["7d", "30d", "90d"],
        Query(description="Time range for growth metrics and time series (7d, 30d, or 90d)"),
    ] = "7d",
) -> DashboardStats:
    """Get dashboard statistics.

    Returns comprehensive dashboard metrics including:
    - Total counts (accounts, users, collections, records)
    - Growth metrics for the selected range (new accounts/users; field names
      ``new_accounts_7d`` / ``new_users_7d`` always reflect the effective ``range``)
    - Previous-period comparison counts of equal length
    - Daily time series for accounts, users, and audit operations (zero-filled)
    - Top collections by record count (top 10 + optional Other bucket)
    - Platform feature counts (hooks, webhooks, workflows, endpoints, macros, …)
    - Jobs status composition and hook/webhook outcome summaries
    - Recent registrations (last 10 users) and recent audit logs
    - System health (database status, storage usage) and active sessions

    Only superadmins can access this endpoint. PII on audit logs is masked unless
    the user belongs to the ``pii_access`` group.

    Performance notes:
    - Record counts use a batched ``UNION ALL`` of ``COUNT(*)`` (not N+1).
    - Automation subsections degrade to zeros if underlying tables fail.
    """
    dashboard_service = DashboardService(session)
    return await dashboard_service.get_dashboard_stats(
        user_groups=current_user.groups,
        account_id=current_user.account_id,
        range=range,
    )
