"""Unit tests for DashboardService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.domain.services import DashboardService
from snackbase.infrastructure.api.schemas import DashboardStats


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def dashboard_service(mock_session):
    """Create a DashboardService instance with mocked session."""
    return DashboardService(mock_session)


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_data(dashboard_service, mock_session):
    """Test get_dashboard_stats returns correct data when data exists."""
    from snackbase.infrastructure.api.schemas import SystemHealthStats

    mock_user1 = MagicMock()
    mock_user1.id = "user1"
    mock_user1.email = "user1@example.com"
    mock_user1.account_id = "AC0001"
    mock_user1.created_at = datetime.now(timezone.utc)
    mock_user1.account = MagicMock()
    mock_user1.account.name = "Test Account"
    mock_user1.account.account_code = "AC0001"

    with (
        patch.object(dashboard_service.account_repo, "count_all", return_value=5),
        patch.object(
            dashboard_service.account_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[2, 1],
        ),
        patch.object(
            dashboard_service.account_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.user_repo, "count_all", return_value=15),
        patch.object(
            dashboard_service.user_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[3, 2],
        ),
        patch.object(
            dashboard_service.user_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.collection_repo, "count_all", return_value=4),
        patch.object(
            dashboard_service.refresh_token_repo, "count_active_sessions", return_value=8
        ),
        patch.object(
            dashboard_service.collection_rule_repo, "count_public_collections", return_value=1
        ),
        patch.object(dashboard_service, "_count_total_records", return_value=100),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
    ):
        dashboard_service.user_repo.get_recent_registrations = AsyncMock(
            return_value=[mock_user1]
        )
        dashboard_service.audit_log_service.list_logs = AsyncMock(return_value=([], 0))
        dashboard_service.audit_log_service.mask_for_display = MagicMock(return_value=[])

        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=10.5
        )

        result = await dashboard_service.get_dashboard_stats(user_groups=[])

        assert isinstance(result, DashboardStats)
        assert result.total_accounts == 5
        assert result.total_users == 15
        assert result.total_collections == 4
        assert result.total_records == 100
        assert result.new_accounts_7d == 2
        assert result.new_users_7d == 3
        assert result.range == "7d"
        assert result.previous_period.new_accounts == 1
        assert result.previous_period.new_users == 2
        assert len(result.time_series.accounts_created) == 7
        assert len(result.time_series.users_created) == 7
        assert all(p.count == 0 for p in result.time_series.accounts_created)
        assert result.active_sessions == 8
        assert result.public_collections_count == 1
        assert len(result.recent_registrations) == 1
        assert result.recent_registrations[0].email == "user1@example.com"
        assert result.system_health.database_status == "connected"
        assert result.system_health.storage_usage_mb == 10.5
        assert result.recent_audit_logs == []


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty_database(dashboard_service):
    """Test get_dashboard_stats with empty database."""
    from snackbase.infrastructure.api.schemas import SystemHealthStats

    with (
        patch.object(dashboard_service.account_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.account_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        ),
        patch.object(
            dashboard_service.account_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.user_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.user_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        ),
        patch.object(
            dashboard_service.user_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            dashboard_service.user_repo,
            "get_recent_registrations",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.collection_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.refresh_token_repo, "count_active_sessions", return_value=0
        ),
        patch.object(
            dashboard_service.collection_rule_repo, "count_public_collections", return_value=0
        ),
        patch.object(
            dashboard_service.audit_log_service,
            "list_logs",
            new_callable=AsyncMock,
            return_value=([], 0),
        ),
        patch.object(
            dashboard_service.audit_log_service, "mask_for_display", return_value=[]
        ),
        patch.object(dashboard_service, "_count_total_records", return_value=0),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
    ):
        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        )

        result = await dashboard_service.get_dashboard_stats(user_groups=[])

        assert result.total_accounts == 0
        assert result.total_users == 0
        assert result.total_collections == 0
        assert result.total_records == 0
        assert result.new_accounts_7d == 0
        assert result.new_users_7d == 0
        assert result.range == "7d"
        assert result.previous_period.new_accounts == 0
        assert result.previous_period.new_users == 0
        assert len(result.time_series.accounts_created) == 7
        assert len(result.time_series.users_created) == 7
        assert result.active_sessions == 0
        assert len(result.recent_registrations) == 0
        assert len(result.recent_audit_logs) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "range_value,expected_days",
    [("7d", 7), ("30d", 30), ("90d", 90)],
)
async def test_get_dashboard_stats_range_series_length(
    dashboard_service, range_value, expected_days
):
    """Test time series length matches selected range."""
    from snackbase.infrastructure.api.schemas import SystemHealthStats

    with (
        patch.object(dashboard_service.account_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.account_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        ),
        patch.object(
            dashboard_service.account_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.user_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.user_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        ),
        patch.object(
            dashboard_service.user_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            dashboard_service.user_repo,
            "get_recent_registrations",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.collection_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.refresh_token_repo, "count_active_sessions", return_value=0
        ),
        patch.object(
            dashboard_service.collection_rule_repo, "count_public_collections", return_value=0
        ),
        patch.object(
            dashboard_service.audit_log_service,
            "list_logs",
            new_callable=AsyncMock,
            return_value=([], 0),
        ),
        patch.object(
            dashboard_service.audit_log_service, "mask_for_display", return_value=[]
        ),
        patch.object(dashboard_service, "_count_total_records", return_value=0),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
    ):
        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        )

        result = await dashboard_service.get_dashboard_stats(
            user_groups=[], range=range_value
        )

        assert result.range == range_value
        assert len(result.time_series.accounts_created) == expected_days
        assert len(result.time_series.users_created) == expected_days


@pytest.mark.asyncio
async def test_get_dashboard_stats_previous_period_math(dashboard_service):
    """Test previous period counts are returned correctly."""
    from snackbase.infrastructure.api.schemas import SystemHealthStats

    with (
        patch.object(dashboard_service.account_repo, "count_all", return_value=10),
        patch.object(
            dashboard_service.account_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[5, 3],  # current, previous
        ),
        patch.object(
            dashboard_service.account_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.user_repo, "count_all", return_value=20),
        patch.object(
            dashboard_service.user_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[8, 4],
        ),
        patch.object(
            dashboard_service.user_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            dashboard_service.user_repo,
            "get_recent_registrations",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(dashboard_service.collection_repo, "count_all", return_value=0),
        patch.object(
            dashboard_service.refresh_token_repo, "count_active_sessions", return_value=0
        ),
        patch.object(
            dashboard_service.collection_rule_repo, "count_public_collections", return_value=0
        ),
        patch.object(
            dashboard_service.audit_log_service,
            "list_logs",
            new_callable=AsyncMock,
            return_value=([], 0),
        ),
        patch.object(
            dashboard_service.audit_log_service, "mask_for_display", return_value=[]
        ),
        patch.object(dashboard_service, "_count_total_records", return_value=0),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
    ):
        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        )

        result = await dashboard_service.get_dashboard_stats(user_groups=[], range="30d")

        assert result.new_accounts_7d == 5
        assert result.new_users_7d == 8
        assert result.previous_period.new_accounts == 3
        assert result.previous_period.new_users == 4
        assert result.range == "30d"
        assert len(result.time_series.accounts_created) == 30


def test_zero_fill_series_fills_missing_days(dashboard_service):
    """Test _zero_fill_series inserts zeros and preserves known counts."""
    end = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    buckets = [
        ("2026-07-17", 2),
        ("2026-07-19", 5),
    ]
    points = dashboard_service._zero_fill_series(buckets, days=7, end=end)

    assert len(points) == 7
    assert points[0].date == "2026-07-13"
    assert points[-1].date == "2026-07-19"
    by_date = {p.date: p.count for p in points}
    assert by_date["2026-07-17"] == 2
    assert by_date["2026-07-19"] == 5
    assert by_date["2026-07-18"] == 0
    assert by_date["2026-07-13"] == 0


@pytest.mark.asyncio
async def test_count_total_records_multiple_collections(dashboard_service, mock_session):
    """Test _count_total_records counts across multiple collections."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("posts",), ("comments",)]
    mock_session.execute.return_value = mock_result

    count_results = [
        MagicMock(scalar_one=lambda: 10),
        MagicMock(scalar_one=lambda: 25),
        MagicMock(scalar_one=lambda: 50),
    ]
    mock_session.execute.side_effect = [mock_result] + count_results

    total = await dashboard_service._count_total_records()

    assert total == 85


@pytest.mark.asyncio
async def test_count_total_records_handles_errors(dashboard_service, mock_session):
    """Test _count_total_records handles table errors gracefully."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("invalid_table",)]
    mock_session.execute.return_value = mock_result

    count_success = MagicMock(scalar_one=lambda: 10)
    mock_session.execute.side_effect = [
        mock_result,
        count_success,
        Exception("Table not found"),
    ]

    total = await dashboard_service._count_total_records()

    assert total == 10


@pytest.mark.asyncio
async def test_get_system_health_database_connected(dashboard_service, mock_session):
    """Test _get_system_health when database is connected."""
    mock_session.execute.return_value = AsyncMock()

    with patch.object(dashboard_service, "_get_storage_usage", return_value=15.75):
        health = await dashboard_service._get_system_health()

        assert health.database_status == "connected"
        assert health.storage_usage_mb == 15.75


@pytest.mark.asyncio
async def test_get_system_health_database_disconnected(dashboard_service, mock_session):
    """Test _get_system_health when database is disconnected."""
    mock_session.execute.side_effect = Exception("Connection failed")

    with patch.object(dashboard_service, "_get_storage_usage", return_value=0.0):
        health = await dashboard_service._get_system_health()

        assert health.database_status == "disconnected"
        assert health.storage_usage_mb == 0.0


def test_get_storage_usage_with_files(dashboard_service):
    """Test _get_storage_usage calculates file sizes correctly."""
    with (
        patch("snackbase.domain.services.dashboard_service.Path") as mock_path,
        patch("snackbase.domain.services.dashboard_service.os.walk") as mock_walk,
        patch("snackbase.domain.services.dashboard_service.os.path.getsize") as mock_getsize,
        patch(
            "snackbase.domain.services.dashboard_service.os.path.exists", return_value=True
        ),
    ):
        mock_path.return_value.exists.return_value = True
        mock_walk.return_value = [
            ("/storage", [], ["file1.txt", "file2.txt"]),
            ("/storage/subdir", [], ["file3.txt"]),
        ]
        mock_getsize.side_effect = [1024, 2048, 512]

        usage_mb = dashboard_service._get_storage_usage()

        assert usage_mb == 0.0


def test_get_storage_usage_no_storage_path(dashboard_service):
    """Test _get_storage_usage returns 0 when storage path doesn't exist."""
    with patch("snackbase.domain.services.dashboard_service.Path") as mock_path:
        mock_path.return_value.exists.return_value = False

        usage_mb = dashboard_service._get_storage_usage()

        assert usage_mb == 0.0
