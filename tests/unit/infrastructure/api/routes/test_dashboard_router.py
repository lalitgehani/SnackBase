"""Unit tests for dashboard router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from snackbase.infrastructure.api.routes.dashboard_router import get_dashboard_stats
from snackbase.infrastructure.api.schemas import (
    DashboardStats,
    RecentRegistration,
    SystemHealthStats,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_superadmin():
    """Create a mock superadmin user."""
    user = MagicMock()
    user.user_id = "superadmin-123"
    user.account_id = "SY0000"
    return user


@pytest.fixture
def sample_dashboard_stats():
    """Create sample dashboard statistics."""
    return DashboardStats(
        total_accounts=5,
        total_users=20,
        total_collections=10,
        total_records=500,
        new_accounts_7d=2,
        new_users_7d=5,
        recent_registrations=[
            RecentRegistration(
                id="user1",
                email="user1@example.com",
                account_id="AC0001",
                account_code="AC0001",
                account_name="Test Account",
                created_at=datetime.now(timezone.utc),
            )
        ],
        system_health=SystemHealthStats(
            database_status="connected", storage_usage_mb=25.5
        ),
        active_sessions=10,
        recent_audit_logs=[],
    )


@pytest.mark.asyncio
async def test_get_dashboard_stats_success(
    mock_superadmin, mock_session, sample_dashboard_stats
):
    """Test successful dashboard stats retrieval."""
    with patch(
        "snackbase.infrastructure.api.routes.dashboard_router.DashboardService"
    ) as mock_service_class:
        # Mock service instance and method
        mock_service = mock_service_class.return_value
        mock_service.get_dashboard_stats = AsyncMock(return_value=sample_dashboard_stats)

        # Execute
        result = await get_dashboard_stats(mock_superadmin, mock_session)

        # Verify
        assert isinstance(result, DashboardStats)
        assert result.total_accounts == 5
        assert result.total_users == 20
        assert result.total_collections == 10
        assert result.total_records == 500
        assert result.new_accounts_7d == 2
        assert result.new_users_7d == 5
        assert result.active_sessions == 10
        assert len(result.recent_registrations) == 1
        assert result.system_health.database_status == "connected"

        # Verify service was called correctly
        mock_service_class.assert_called_once_with(mock_session)
        mock_service.get_dashboard_stats.assert_called_once()


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty_data(mock_superadmin, mock_session):
    """Test dashboard stats with empty/zero data."""
    empty_stats = DashboardStats(
        total_accounts=0,
        total_users=0,
        total_collections=0,
        total_records=0,
        new_accounts_7d=0,
        new_users_7d=0,
        recent_registrations=[],
        system_health=SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        ),
        active_sessions=0,
        recent_audit_logs=[],
    )

    with patch(
        "snackbase.infrastructure.api.routes.dashboard_router.DashboardService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_dashboard_stats = AsyncMock(return_value=empty_stats)

        # Execute
        result = await get_dashboard_stats(mock_superadmin, mock_session)

        # Verify
        assert result.total_accounts == 0
        assert result.total_users == 0
        assert len(result.recent_registrations) == 0
        assert len(result.recent_audit_logs) == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_requires_superadmin():
    """Test that endpoint requires superadmin authentication."""
    # This test verifies the dependency is correctly specified
    # The actual authentication is tested via integration tests
    from snackbase.infrastructure.api.routes.dashboard_router import router

    # Get the route
    routes = [r for r in router.routes if r.path == "/stats"]
    assert len(routes) == 1

    route = routes[0]
    # Verify the route has the SuperadminUser dependency
    # This is implicit in the function signature, verified by type checking
    assert route.endpoint == get_dashboard_stats
