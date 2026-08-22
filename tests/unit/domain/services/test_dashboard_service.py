"""Unit tests for DashboardService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.domain.services import DashboardService
from snackbase.infrastructure.api.schemas import (
    CollectionRecordCount,
    DashboardStats,
    FeatureCounts,
    HookExecutionsSummary,
    JobsByStatus,
    SystemHealthStats,
    WebhookDeliveriesSummary,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def dashboard_service(mock_session):
    """Create a DashboardService instance with mocked session."""
    return DashboardService(mock_session)


def _patch_empty_stats(dashboard_service):
    """Context manager stacking common empty-stats repo mocks."""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch.object(dashboard_service.account_repo, "count_all", return_value=0))
    stack.enter_context(
        patch.object(
            dashboard_service.account_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.account_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        )
    )
    stack.enter_context(patch.object(dashboard_service.user_repo, "count_all", return_value=0))
    stack.enter_context(
        patch.object(
            dashboard_service.user_repo,
            "count_created_between",
            new_callable=AsyncMock,
            side_effect=[0, 0],
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.user_repo,
            "count_created_by_day",
            new_callable=AsyncMock,
            return_value=[],
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.user_repo,
            "get_recent_registrations",
            new_callable=AsyncMock,
            return_value=[],
        )
    )
    stack.enter_context(
        patch.object(dashboard_service.collection_repo, "count_all", return_value=0)
    )
    stack.enter_context(
        patch.object(
            dashboard_service.refresh_token_repo, "count_active_sessions", return_value=0
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.collection_rule_repo, "count_public_collections", return_value=0
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.audit_log_repo,
            "count_by_operation_by_day",
            new_callable=AsyncMock,
            return_value=[],
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service.audit_log_service,
            "list_logs",
            new_callable=AsyncMock,
            return_value=([], 0),
        )
    )
    stack.enter_context(
        patch.object(dashboard_service.audit_log_service, "mask_for_display", return_value=[])
    )
    stack.enter_context(
        patch.object(
            dashboard_service,
            "_count_records_by_collection",
            new_callable=AsyncMock,
            return_value=(0, []),
        )
    )
    # Phase 3 automation aggregates (zero defaults)
    stack.enter_context(
        patch.object(
            dashboard_service,
            "_get_feature_counts",
            new_callable=AsyncMock,
            return_value=FeatureCounts(),
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service,
            "_get_jobs_by_status",
            new_callable=AsyncMock,
            return_value=JobsByStatus(),
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service,
            "_get_hook_executions_summary",
            new_callable=AsyncMock,
            return_value=HookExecutionsSummary(),
        )
    )
    stack.enter_context(
        patch.object(
            dashboard_service,
            "_get_webhook_deliveries_summary",
            new_callable=AsyncMock,
            return_value=WebhookDeliveriesSummary(),
        )
    )
    return stack


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_data(dashboard_service, mock_session):
    """Test get_dashboard_stats returns correct data when data exists."""
    mock_user1 = MagicMock()
    mock_user1.id = "user1"
    mock_user1.email = "user1@example.com"
    mock_user1.account_id = "AC0001"
    mock_user1.created_at = datetime.now(UTC)
    mock_user1.account = MagicMock()
    mock_user1.account.name = "Test Account"
    mock_user1.account.account_code = "AC0001"

    ranked = [
        CollectionRecordCount(name="posts", count=70),
        CollectionRecordCount(name="comments", count=30),
    ]

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
        patch.object(
            dashboard_service,
            "_count_records_by_collection",
            new_callable=AsyncMock,
            return_value=(100, ranked),
        ),
        patch.object(
            dashboard_service.audit_log_repo,
            "count_by_operation_by_day",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            dashboard_service,
            "_get_feature_counts",
            new_callable=AsyncMock,
            return_value=FeatureCounts(),
        ),
        patch.object(
            dashboard_service,
            "_get_jobs_by_status",
            new_callable=AsyncMock,
            return_value=JobsByStatus(),
        ),
        patch.object(
            dashboard_service,
            "_get_hook_executions_summary",
            new_callable=AsyncMock,
            return_value=HookExecutionsSummary(),
        ),
        patch.object(
            dashboard_service,
            "_get_webhook_deliveries_summary",
            new_callable=AsyncMock,
            return_value=WebhookDeliveriesSummary(),
        ),
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
        assert len(result.time_series.audit_by_operation) == 7
        assert all(p.count == 0 for p in result.time_series.accounts_created)
        assert all(
            p.create == 0 and p.update == 0 and p.delete == 0
            for p in result.time_series.audit_by_operation
        )
        assert result.active_sessions == 8
        assert result.public_collections_count == 1
        assert len(result.records_by_collection) == 2
        assert result.records_by_collection[0].name == "posts"
        assert result.records_by_collection[0].count == 70
        assert len(result.recent_registrations) == 1
        assert result.recent_registrations[0].email == "user1@example.com"
        assert result.system_health.database_status == "connected"
        assert result.system_health.storage_usage_mb == 10.5
        assert result.recent_audit_logs == []
        # Phase 3 fields present (graceful defaults when not mocked with data)
        assert result.feature_counts.hooks == 0
        assert result.jobs_by_status.pending == 0
        assert result.hook_executions_summary.success == 0
        assert result.webhook_deliveries_summary.delivered == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty_database(dashboard_service):
    """Test get_dashboard_stats with empty database."""
    with (
        _patch_empty_stats(dashboard_service),
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
        assert len(result.time_series.audit_by_operation) == 7
        assert result.records_by_collection == []
        assert result.active_sessions == 0
        assert len(result.recent_registrations) == 0
        assert len(result.recent_audit_logs) == 0
        assert result.feature_counts.hooks == 0
        assert result.jobs_by_status.dead == 0
        assert result.hook_executions_summary.failed == 0
        assert result.webhook_deliveries_summary.failed == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "range_value,expected_days",
    [("7d", 7), ("30d", 30), ("90d", 90)],
)
async def test_get_dashboard_stats_range_series_length(
    dashboard_service, range_value, expected_days
):
    """Test time series length matches selected range including audit series."""
    with (
        _patch_empty_stats(dashboard_service),
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
        assert len(result.time_series.audit_by_operation) == expected_days


@pytest.mark.asyncio
async def test_get_dashboard_stats_previous_period_math(dashboard_service):
    """Test previous period counts are returned correctly."""
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
            dashboard_service.audit_log_repo,
            "count_by_operation_by_day",
            new_callable=AsyncMock,
            return_value=[],
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
        patch.object(
            dashboard_service,
            "_count_records_by_collection",
            new_callable=AsyncMock,
            return_value=(0, []),
        ),
        patch.object(
            dashboard_service,
            "_get_feature_counts",
            new_callable=AsyncMock,
            return_value=FeatureCounts(),
        ),
        patch.object(
            dashboard_service,
            "_get_jobs_by_status",
            new_callable=AsyncMock,
            return_value=JobsByStatus(),
        ),
        patch.object(
            dashboard_service,
            "_get_hook_executions_summary",
            new_callable=AsyncMock,
            return_value=HookExecutionsSummary(),
        ),
        patch.object(
            dashboard_service,
            "_get_webhook_deliveries_summary",
            new_callable=AsyncMock,
            return_value=WebhookDeliveriesSummary(),
        ),
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
        assert len(result.time_series.audit_by_operation) == 30


def test_zero_fill_series_fills_missing_days(dashboard_service):
    """Test _zero_fill_series inserts zeros and preserves known counts."""
    end = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)
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


def test_zero_fill_audit_series_fills_missing_days(dashboard_service):
    """Test audit series zero-fill and operation aggregation."""
    end = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)
    buckets = [
        ("2026-07-17", "CREATE", 3),
        ("2026-07-17", "UPDATE", 1),
        ("2026-07-19", "DELETE", 2),
        ("2026-07-19", "create", 1),  # case-insensitive merge
    ]
    points = dashboard_service._zero_fill_audit_series(buckets, days=7, end=end)

    assert len(points) == 7
    assert points[0].date == "2026-07-13"
    assert points[-1].date == "2026-07-19"
    by_date = {p.date: p for p in points}
    assert by_date["2026-07-17"].create == 3
    assert by_date["2026-07-17"].update == 1
    assert by_date["2026-07-17"].delete == 0
    assert by_date["2026-07-19"].create == 1
    assert by_date["2026-07-19"].delete == 2
    assert by_date["2026-07-18"].create == 0
    assert by_date["2026-07-13"].update == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_audit_series_from_repo(dashboard_service):
    """Test audit_by_operation is populated from repository buckets."""
    end_day = datetime.now(UTC).date().isoformat()
    buckets = [(end_day, "CREATE", 4), (end_day, "UPDATE", 2)]

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
            dashboard_service.audit_log_repo,
            "count_by_operation_by_day",
            new_callable=AsyncMock,
            return_value=buckets,
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
        patch.object(
            dashboard_service,
            "_count_records_by_collection",
            new_callable=AsyncMock,
            return_value=(0, []),
        ),
        patch.object(
            dashboard_service,
            "_get_feature_counts",
            new_callable=AsyncMock,
            return_value=FeatureCounts(),
        ),
        patch.object(
            dashboard_service,
            "_get_jobs_by_status",
            new_callable=AsyncMock,
            return_value=JobsByStatus(),
        ),
        patch.object(
            dashboard_service,
            "_get_hook_executions_summary",
            new_callable=AsyncMock,
            return_value=HookExecutionsSummary(),
        ),
        patch.object(
            dashboard_service,
            "_get_webhook_deliveries_summary",
            new_callable=AsyncMock,
            return_value=WebhookDeliveriesSummary(),
        ),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
    ):
        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=0.0
        )

        result = await dashboard_service.get_dashboard_stats(user_groups=[], range="7d")

        assert len(result.time_series.audit_by_operation) == 7
        last = result.time_series.audit_by_operation[-1]
        assert last.date == end_day
        assert last.create == 4
        assert last.update == 2
        assert last.delete == 0


@pytest.mark.asyncio
async def test_count_records_by_collection_top_n_and_other(dashboard_service, mock_session):
    """Test ranking, top-N cap, and Other bucket (batched UNION ALL)."""
    # 12 collections with decreasing counts
    names = [(f"col{i}",) for i in range(12)]
    mock_names = MagicMock()
    mock_names.fetchall.return_value = names

    # Single batch result with all (name, count) pairs
    batch_rows = [(f"col{i}", 100 - i) for i in range(12)]
    mock_batch = MagicMock()
    mock_batch.fetchall.return_value = batch_rows

    mock_session.execute.side_effect = [mock_names, mock_batch]

    total, ranked = await dashboard_service._count_records_by_collection(top_n=10)

    assert total == sum(range(89, 101))  # 100+99+...+89
    assert len(ranked) == 11  # 10 named + Other
    assert ranked[0].name == "col0"
    assert ranked[0].count == 100
    assert ranked[9].name == "col9"
    assert ranked[10].name == "Other"
    assert ranked[10].count == 90 + 89  # col10 + col11
    # Batch path: names query + one UNION ALL (not N COUNT queries)
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_count_records_by_collection_batch_is_o1_round_trips(
    dashboard_service, mock_session
):
    """Many collections still use only 2 executes (names + UNION ALL)."""
    names = [(f"c{i}",) for i in range(50)]
    mock_names = MagicMock()
    mock_names.fetchall.return_value = names
    mock_batch = MagicMock()
    mock_batch.fetchall.return_value = [(f"c{i}", i) for i in range(50)]
    mock_session.execute.side_effect = [mock_names, mock_batch]

    total, ranked = await dashboard_service._count_records_by_collection(top_n=10)

    assert total == sum(range(50))
    assert len(ranked) == 11  # top 10 + Other
    assert mock_session.execute.call_count == 2
    # UNION ALL SQL should mention multiple tables
    batch_sql = str(mock_session.execute.call_args_list[1].args[0])
    assert "UNION ALL" in batch_sql
    assert "COUNT(*)" in batch_sql


@pytest.mark.asyncio
async def test_count_total_records_multiple_collections(dashboard_service, mock_session):
    """Test _count_total_records counts across multiple collections (batched)."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("posts",), ("comments",)]

    mock_batch = MagicMock()
    mock_batch.fetchall.return_value = [
        ("users", 10),
        ("posts", 25),
        ("comments", 50),
    ]
    mock_session.execute.side_effect = [mock_result, mock_batch]

    total = await dashboard_service._count_total_records()

    assert total == 85


@pytest.mark.asyncio
async def test_count_records_batch_fallback_on_error(dashboard_service, mock_session):
    """When batch UNION fails, fall back to sequential skip-per-table."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("users",), ("invalid_table",)]

    count_success = MagicMock(scalar_one=lambda: 10)
    mock_session.execute.side_effect = [
        mock_result,  # SELECT name FROM collections
        Exception("Table not found"),  # batch UNION fails
        count_success,  # sequential users OK
        Exception("Table not found"),  # sequential invalid_table skip
    ]

    total, ranked = await dashboard_service._count_records_by_collection()

    assert total == 10
    assert len(ranked) == 1
    assert ranked[0].name == "users"
    assert ranked[0].count == 10


@pytest.mark.asyncio
async def test_count_records_empty_collections(dashboard_service, mock_session):
    """Empty collections table returns zeros without batch query."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result

    total, ranked = await dashboard_service._count_records_by_collection()

    assert total == 0
    assert ranked == []
    assert mock_session.execute.call_count == 1


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


@pytest.mark.asyncio
async def test_get_feature_counts_from_repos(dashboard_service):
    """Test feature_counts aggregates from repository count helpers."""
    with (
        patch.object(
            dashboard_service.hook_repo, "count_all", new_callable=AsyncMock, return_value=10
        ),
        patch.object(
            dashboard_service.hook_repo,
            "count_enabled",
            new_callable=AsyncMock,
            return_value=7,
        ),
        patch.object(
            dashboard_service.webhook_repo,
            "count_all",
            new_callable=AsyncMock,
            return_value=5,
        ),
        patch.object(
            dashboard_service.webhook_repo,
            "count_enabled",
            new_callable=AsyncMock,
            return_value=4,
        ),
        patch.object(
            dashboard_service.workflow_repo,
            "count_all",
            new_callable=AsyncMock,
            return_value=3,
        ),
        patch.object(
            dashboard_service.endpoint_repo,
            "count_all",
            new_callable=AsyncMock,
            return_value=8,
        ),
        patch.object(
            dashboard_service.macro_repo, "count_all", new_callable=AsyncMock, return_value=2
        ),
        patch.object(
            dashboard_service.api_key_repo,
            "count_active",
            new_callable=AsyncMock,
            return_value=6,
        ),
        patch.object(
            dashboard_service.invitation_repo,
            "count_pending",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        counts = await dashboard_service._get_feature_counts()

    assert counts.hooks == 10
    assert counts.hooks_enabled == 7
    assert counts.webhooks == 5
    assert counts.webhooks_enabled == 4
    assert counts.workflows == 3
    assert counts.endpoints == 8
    assert counts.macros == 2
    assert counts.api_keys_active == 6
    assert counts.invitations_pending == 1


@pytest.mark.asyncio
async def test_get_feature_counts_graceful_degrade(dashboard_service):
    """Test feature_counts returns zeros when a repository raises."""
    with patch.object(
        dashboard_service.hook_repo,
        "count_all",
        new_callable=AsyncMock,
        side_effect=Exception("table missing"),
    ):
        counts = await dashboard_service._get_feature_counts()

    assert counts == FeatureCounts()


@pytest.mark.asyncio
async def test_get_jobs_by_status(dashboard_service):
    """Test jobs_by_status maps JobRepository.get_stats keys."""
    with patch.object(
        dashboard_service.job_repo,
        "get_stats",
        new_callable=AsyncMock,
        return_value={
            "pending": 1,
            "running": 2,
            "completed": 10,
            "failed": 3,
            "retrying": 1,
            "dead": 2,
        },
    ):
        result = await dashboard_service._get_jobs_by_status()

    assert result.pending == 1
    assert result.running == 2
    assert result.completed == 10
    assert result.failed == 3
    assert result.retrying == 1
    assert result.dead == 2


@pytest.mark.asyncio
async def test_get_jobs_by_status_graceful_degrade(dashboard_service):
    """Test jobs_by_status returns zeros on failure."""
    with patch.object(
        dashboard_service.job_repo,
        "get_stats",
        new_callable=AsyncMock,
        side_effect=Exception("db error"),
    ):
        result = await dashboard_service._get_jobs_by_status()

    assert result == JobsByStatus()


@pytest.mark.asyncio
async def test_get_hook_executions_summary(dashboard_service):
    """Test hook execution summary from range-scoped aggregation."""
    with patch.object(
        dashboard_service.hook_execution_repo,
        "count_by_status_between",
        new_callable=AsyncMock,
        return_value={"success": 20, "failed": 3, "partial": 1},
    ):
        start = datetime.now(UTC)
        end = start
        result = await dashboard_service._get_hook_executions_summary(start, end)

    assert result.success == 20
    assert result.failed == 3
    assert result.partial == 1


@pytest.mark.asyncio
async def test_get_webhook_deliveries_summary(dashboard_service):
    """Test webhook delivery summary from range-scoped aggregation."""
    with patch.object(
        dashboard_service.webhook_delivery_repo,
        "count_by_status_between",
        new_callable=AsyncMock,
        return_value={"delivered": 15, "failed": 2, "pending": 1, "retrying": 0},
    ):
        start = datetime.now(UTC)
        end = start
        result = await dashboard_service._get_webhook_deliveries_summary(start, end)

    assert result.delivered == 15
    assert result.failed == 2
    assert result.pending == 1
    assert result.retrying == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_includes_phase3_automation(dashboard_service):
    """Test full stats payload includes Phase 3 automation fields with data."""
    with (
        _patch_empty_stats(dashboard_service),
        patch.object(dashboard_service, "_get_system_health") as mock_health,
        patch.object(
            dashboard_service,
            "_get_feature_counts",
            new_callable=AsyncMock,
            return_value=FeatureCounts(hooks=4, hooks_enabled=3, webhooks=2),
        ),
        patch.object(
            dashboard_service,
            "_get_jobs_by_status",
            new_callable=AsyncMock,
            return_value=JobsByStatus(dead=2, completed=5),
        ),
        patch.object(
            dashboard_service,
            "_get_hook_executions_summary",
            new_callable=AsyncMock,
            return_value=HookExecutionsSummary(success=9, failed=1),
        ),
        patch.object(
            dashboard_service,
            "_get_webhook_deliveries_summary",
            new_callable=AsyncMock,
            return_value=WebhookDeliveriesSummary(delivered=4, failed=1),
        ),
    ):
        mock_health.return_value = SystemHealthStats(
            database_status="connected", storage_usage_mb=1.0
        )

        result = await dashboard_service.get_dashboard_stats(user_groups=[], range="7d")

    assert result.feature_counts.hooks == 4
    assert result.feature_counts.hooks_enabled == 3
    assert result.feature_counts.webhooks == 2
    assert result.jobs_by_status.dead == 2
    assert result.jobs_by_status.completed == 5
    assert result.hook_executions_summary.success == 9
    assert result.hook_executions_summary.failed == 1
    assert result.webhook_deliveries_summary.delivered == 4
    assert result.webhook_deliveries_summary.failed == 1
