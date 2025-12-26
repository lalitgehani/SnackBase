"""Dashboard API routes.

Provides endpoints for dashboard statistics and metrics.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import DashboardStats
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.domain.services import DashboardService

router = APIRouter()


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    response_model=DashboardStats,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def get_dashboard_stats(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardStats:
    """Get dashboard statistics.

    Returns comprehensive dashboard metrics including:
    - Total counts (accounts, users, collections, records)
    - Growth metrics (new accounts/users in last 7 days)
    - Recent registrations (last 10 users)
    - System health (database status, storage usage)
    - Active sessions count
    - Recent audit logs (placeholder until F3.7)

    Only superadmins (users in the SY0000 system account) can access this endpoint.
    """
    dashboard_service = DashboardService(session)
    return await dashboard_service.get_dashboard_stats()
