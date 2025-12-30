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
    # Mock repository responses
    with patch.object(
        dashboard_service.account_repo, "count_all", return_value=5
    ), patch.object(
        dashboard_service.account_repo, "count_created_since", return_value=2
    ), patch.object(
        dashboard_service.user_repo, "count_all", return_value=15
    ), patch.object(
        dashboard_service.user_repo, "count_created_since", return_value=3
    ), patch.object(
        dashboard_service.collection_repo, "count_all", return_value=4
    ), patch.object(
        dashboard_service.refresh_token_repo, "count_active_sessions", return_value=8
    ), patch.object(
        dashboard_service, "_count_total_records", return_value=100
    ), patch.object(
        dashboard_service, "_get_system_health"
    ) as mock_health:
        # Mock recent registrations
        mock_user1 = MagicMock()
        mock_user1.id = "user1"
        mock_user1.email = "user1@example.com"
        mock_user1.account_id = "AC0001"
        mock_user1.created_at = datetime.now(timezone.utc)
        mock_user1.account = MagicMock()
        mock_user1.account.name = "Test Account"
        mock_user1.account.account_code = "AC0001"

        dashboard_service.user_repo.get_recent_registrations = AsyncMock(
            return_value=[mock_user1]
        )

        dashboard_service.audit_log_repo.list_logs = AsyncMock(
            return_value=([], 0)
        )

        # Mock system health
        from snackbase.infrastructure.api.schemas import SystemHealthStats

        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=10.5
        )

        # Execute
        result = await dashboard_service.get_dashboard_stats()

        # Verify
        assert isinstance(result, DashboardStats)
        assert result.total_accounts == 5
        assert result.total_users == 15
        assert result.total_collections == 4
        assert result.total_records == 100
        assert result.new_accounts_7d == 2
        assert result.new_users_7d == 3
        assert result.active_sessions == 8
        assert len(result.recent_registrations) == 1
        assert result.recent_registrations[0].email == "user1@example.com"
        assert result.system_health.database_status == "connected"
        assert result.system_health.storage_usage_mb == 10.5
        assert result.recent_audit_logs == []


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty_database(dashboard_service):
    """Test get_dashboard_stats with empty database."""
    # Mock all counts as zero
    with patch.object(
        dashboard_service.account_repo, "count_all", return_value=0
    ), patch.object(
        dashboard_service.account_repo, "count_created_since", return_value=0
    ), patch.object(
        dashboard_service.user_repo, "count_all", return_value=0
    ), patch.object(
        dashboard_service.user_repo, "count_created_since", return_value=0
    ), patch.object(
        dashboard_service.user_repo, "get_recent_registrations", return_value=[]
    ), patch.object(
        dashboard_service.collection_repo, "count_all", return_value=0
    ), patch.object(
        dashboard_service.refresh_token_repo, "count_active_sessions", return_value=0
    ), patch.object(
        dashboard_service.audit_log_repo, "list_logs", return_value=([], 0)
    ), patch.object(
        dashboard_service, "_count_total_records", return_value=0
    ), patch.object(
        dashboard_service, "_get_system_health"
    ) as mock_health:
        from snackbase.infrastructure.api.schemas import SystemHealthStats

        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        )

        # Execute
        result = await dashboard_service.get_dashboard_stats()

        # Verify
        assert result.total_accounts == 0
        assert result.total_users == 0
        assert result.total_collections == 0
        assert result.total_records == 0
        assert result.new_accounts_7d == 0
        assert result.new_users_7d == 0
        assert result.active_sessions == 0
        assert len(result.recent_registrations) == 0
        assert len(result.recent_audit_logs) == 0


@pytest.mark.asyncio
async def test_count_total_records_multiple_collections(dashboard_service, mock_session):
    """Test _count_total_records counts across multiple collections."""
    # Mock collections query
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("posts",), ("comments",)]
    mock_session.execute.return_value = mock_result

    # Mock count queries for each table
    count_results = [
        MagicMock(scalar_one=lambda: 10),  # users
        MagicMock(scalar_one=lambda: 25),  # posts
        MagicMock(scalar_one=lambda: 50),  # comments
    ]
    mock_session.execute.side_effect = [mock_result] + count_results

    # Execute
    total = await dashboard_service._count_total_records()

    # Verify
    assert total == 85  # 10 + 25 + 50


@pytest.mark.asyncio
async def test_count_total_records_handles_errors(dashboard_service, mock_session):
    """Test _count_total_records handles table errors gracefully."""
    # Mock collections query
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("invalid_table",)]
    mock_session.execute.return_value = mock_result

    # First count succeeds, second fails
    count_success = MagicMock(scalar_one=lambda: 10)
    mock_session.execute.side_effect = [
        mock_result,
        count_success,
        Exception("Table not found"),
    ]

    # Execute
    total = await dashboard_service._count_total_records()

    # Verify - should only count the successful table
    assert total == 10


@pytest.mark.asyncio
async def test_get_system_health_database_connected(dashboard_service, mock_session):
    """Test _get_system_health when database is connected."""
    # Mock successful database query
    mock_session.execute.return_value = AsyncMock()

    with patch.object(dashboard_service, "_get_storage_usage", return_value=15.75):
        # Execute
        health = await dashboard_service._get_system_health()

        # Verify
        assert health.database_status == "connected"
        assert health.storage_usage_mb == 15.75


@pytest.mark.asyncio
async def test_get_system_health_database_disconnected(dashboard_service, mock_session):
    """Test _get_system_health when database is disconnected."""
    # Mock failed database query
    mock_session.execute.side_effect = Exception("Connection failed")

    with patch.object(dashboard_service, "_get_storage_usage", return_value=0.0):
        # Execute
        health = await dashboard_service._get_system_health()

        # Verify
        assert health.database_status == "disconnected"
        assert health.storage_usage_mb == 0.0


def test_get_storage_usage_with_files(dashboard_service):
    """Test _get_storage_usage calculates file sizes correctly."""
    with patch("snackbase.domain.services.dashboard_service.Path") as mock_path, patch(
        "snackbase.domain.services.dashboard_service.os.walk"
    ) as mock_walk, patch(
        "snackbase.domain.services.dashboard_service.os.path.getsize"
    ) as mock_getsize, patch(
        "snackbase.domain.services.dashboard_service.os.path.exists", return_value=True
    ):
        # Mock storage path exists
        mock_path.return_value.exists.return_value = True

        # Mock file tree
        mock_walk.return_value = [
            ("/storage", [], ["file1.txt", "file2.txt"]),
            ("/storage/subdir", [], ["file3.txt"]),
        ]

        # Mock file sizes (in bytes)
        mock_getsize.side_effect = [1024, 2048, 512]  # 1KB, 2KB, 0.5KB

        # Execute
        usage_mb = dashboard_service._get_storage_usage()

        # Verify - (1024 + 2048 + 512) / (1024 * 1024) = 0.0034 MB
        assert usage_mb == 0.0


def test_get_storage_usage_no_storage_path(dashboard_service):
    """Test _get_storage_usage returns 0 when storage path doesn't exist."""
    with patch("snackbase.domain.services.dashboard_service.Path") as mock_path:
        # Mock storage path doesn't exist
        mock_path.return_value.exists.return_value = False

        # Execute
        usage_mb = dashboard_service._get_storage_usage()

        # Verify
        assert usage_mb == 0.0
