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
    - Growth metrics for the selected range (new accounts/users)
    - Previous-period comparison counts
    - Daily time series for accounts and users (zero-filled)
    - Recent registrations (last 10 users)
    - System health (database status, storage usage)
    - Active sessions count
    - Recent audit logs (PII masked based on user group membership)

    Only superadmins (users in the system account with nil UUID) can access this endpoint.
    PII is masked unless the user belongs to the 'pii_access' group.
    """
    dashboard_service = DashboardService(session)
    return await dashboard_service.get_dashboard_stats(
        user_groups=current_user.groups,
        account_id=current_user.account_id,
        range=range,
    )
