"""Dashboard service for aggregating statistics.

Provides methods for collecting and aggregating dashboard metrics
from various repositories.
"""

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services.audit_log_service import AuditLogService
from snackbase.infrastructure.api.schemas import (
    AuditLogResponse,
    AuditOperationPoint,
    CollectionRecordCount,
    DashboardStats,
    FeatureCounts,
    HookExecutionsSummary,
    JobsByStatus,
    PreviousPeriodStats,
    RecentRegistration,
    SystemHealthStats,
    TimeSeriesPoint,
    TimeSeriesStats,
    WebhookDeliveriesSummary,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    APIKeyRepository,
    CollectionRepository,
    InvitationRepository,
    MacroRepository,
    RefreshTokenRepository,
    UserRepository,
)
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)
from snackbase.infrastructure.persistence.repositories.collection_rule_repository import (
    CollectionRuleRepository,
)
from snackbase.infrastructure.persistence.repositories.endpoint_repository import (
    EndpointRepository,
)
from snackbase.infrastructure.persistence.repositories.hook_execution_repository import (
    HookExecutionRepository,
)
from snackbase.infrastructure.persistence.repositories.hook_repository import (
    HookRepository,
)
from snackbase.infrastructure.persistence.repositories.job_repository import (
    JobRepository,
)
from snackbase.infrastructure.persistence.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookRepository,
)
from snackbase.infrastructure.persistence.repositories.workflow_repository import (
    WorkflowRepository,
)
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)

DashboardRange = Literal["7d", "30d", "90d"]

RANGE_DAYS: dict[DashboardRange, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

# Safe dynamic table identifier: col_ + lowercase alphanumeric/underscore only.
_COLLECTION_TABLE_RE = re.compile(r"^col_[a-z0-9_]+$")


class DashboardService:
    """Service for aggregating dashboard statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the dashboard service.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.account_repo = AccountRepository(session)
        self.user_repo = UserRepository(session)
        self.collection_repo = CollectionRepository(session)
        self.collection_rule_repo = CollectionRuleRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)
        self.audit_log_repo = AuditLogRepository(session)
        self.audit_log_service = AuditLogService(session)
        # Phase 3 automation / integrations repos
        self.job_repo = JobRepository(session)
        self.hook_repo = HookRepository(session)
        self.hook_execution_repo = HookExecutionRepository(session)
        self.webhook_repo = WebhookRepository(session)
        self.webhook_delivery_repo = WebhookDeliveryRepository(session)
        self.workflow_repo = WorkflowRepository(session)
        self.endpoint_repo = EndpointRepository(session)
        self.macro_repo = MacroRepository(session)
        self.api_key_repo = APIKeyRepository(session)
        self.invitation_repo = InvitationRepository(session)

    async def get_dashboard_stats(
        self,
        user_groups: list[str],
        account_id: str | None = None,
        range: DashboardRange = "7d",
    ) -> DashboardStats:
        """Get all dashboard statistics.

        Args:
            user_groups: List of group names the user belongs to for PII masking.
            account_id: Optional account ID for superadmin PII bypass.
            range: Time range for growth metrics (`7d`, `30d`, or `90d`).

        Returns:
            DashboardStats with all metrics populated.
        """
        now = datetime.now(UTC)
        days = RANGE_DAYS[range]
        range_start = now - timedelta(days=days)
        previous_start = now - timedelta(days=days * 2)

        # Get total counts
        total_accounts = await self.account_repo.count_all()
        total_users = await self.user_repo.count_all()
        total_collections = await self.collection_repo.count_all()
        total_records, records_by_collection = await self._count_records_by_collection()

        # Growth metrics for selected range (field names kept as *_7d for compatibility)
        new_accounts_7d = await self.account_repo.count_created_between(range_start, now)
        new_users_7d = await self.user_repo.count_created_between(range_start, now)

        previous_new_accounts = await self.account_repo.count_created_between(
            previous_start, range_start
        )
        previous_new_users = await self.user_repo.count_created_between(
            previous_start, range_start
        )

        # Daily time series (exactly `days` points, zero-filled for continuous axes)
        accounts_by_day = await self.account_repo.count_created_by_day(range_start, now)
        users_by_day = await self.user_repo.count_created_by_day(range_start, now)
        audit_by_day = await self.audit_log_repo.count_by_operation_by_day(
            range_start, now
        )
        time_series = TimeSeriesStats(
            accounts_created=self._zero_fill_series(accounts_by_day, days, now),
            users_created=self._zero_fill_series(users_by_day, days, now),
            audit_by_operation=self._zero_fill_audit_series(audit_by_day, days, now),
        )

        # Get recent registrations
        recent_users = await self.user_repo.get_recent_registrations(limit=10)
        recent_registrations = [
            RecentRegistration(
                id=user.id,
                email=user.email,
                account_id=user.account_id,
                account_code=user.account.account_code if user.account else "UNKNOWN",
                account_name=user.account.name if user.account else "Unknown",
                created_at=user.created_at,
            )
            for user in recent_users
        ]

        # Get system health
        system_health = await self._get_system_health()

        # Get public collections count
        public_collections_count = await self.collection_rule_repo.count_public_collections()

        # Get active sessions count
        active_sessions = await self.refresh_token_repo.count_active_sessions()

        # Phase 3: automation and integrations (graceful degrade to zeros)
        feature_counts = await self._get_feature_counts()
        jobs_by_status = await self._get_jobs_by_status()
        hook_executions_summary = await self._get_hook_executions_summary(
            range_start, now
        )
        webhook_deliveries_summary = await self._get_webhook_deliveries_summary(
            range_start, now
        )

        # Get recent audit logs (last 20) - with PII masking (returns dicts)
        logs, _ = await self.audit_log_service.list_logs(
            limit=20, sort_by="occurred_at", sort_order="desc"
        )
        masked_logs = self.audit_log_service.mask_for_display(
            logs, user_groups, account_id
        )
        recent_audit_logs = [AuditLogResponse(**log) for log in masked_logs]

        return DashboardStats(
            total_accounts=total_accounts,
            total_users=total_users,
            total_collections=total_collections,
            total_records=total_records,
            new_accounts_7d=new_accounts_7d,
            new_users_7d=new_users_7d,
            range=range,
            previous_period=PreviousPeriodStats(
                new_accounts=previous_new_accounts,
                new_users=previous_new_users,
            ),
            time_series=time_series,
            recent_registrations=recent_registrations,
            system_health=system_health,
            active_sessions=active_sessions,
            public_collections_count=public_collections_count,
            records_by_collection=records_by_collection,
            feature_counts=feature_counts,
            jobs_by_status=jobs_by_status,
            hook_executions_summary=hook_executions_summary,
            webhook_deliveries_summary=webhook_deliveries_summary,
            recent_audit_logs=recent_audit_logs,
        )

    async def _get_feature_counts(self) -> FeatureCounts:
        """Aggregate platform feature adoption counts.

        Returns zeros if any underlying table is missing or query fails.
        """
        try:
            return FeatureCounts(
                hooks=await self.hook_repo.count_all(),
                hooks_enabled=await self.hook_repo.count_enabled(),
                webhooks=await self.webhook_repo.count_all(),
                webhooks_enabled=await self.webhook_repo.count_enabled(),
                workflows=await self.workflow_repo.count_all(),
                endpoints=await self.endpoint_repo.count_all(),
                macros=await self.macro_repo.count_all(),
                api_keys_active=await self.api_key_repo.count_active(),
                invitations_pending=await self.invitation_repo.count_pending(),
            )
        except Exception:
            logger.warning(
                "dashboard_feature_counts_failed",
                exc_info=True,
            )
            return FeatureCounts()

    async def _get_jobs_by_status(self) -> JobsByStatus:
        """Get live job queue composition by status."""
        try:
            stats = await self.job_repo.get_stats()
            return JobsByStatus(
                pending=stats.get("pending", 0),
                running=stats.get("running", 0),
                completed=stats.get("completed", 0),
                failed=stats.get("failed", 0),
                retrying=stats.get("retrying", 0),
                dead=stats.get("dead", 0),
            )
        except Exception:
            logger.warning("dashboard_jobs_by_status_failed", exc_info=True)
            return JobsByStatus()

    async def _get_hook_executions_summary(
        self, start: datetime, end: datetime
    ) -> HookExecutionsSummary:
        """Get hook execution outcomes for the selected range."""
        try:
            stats = await self.hook_execution_repo.count_by_status_between(start, end)
            return HookExecutionsSummary(
                success=stats.get("success", 0),
                failed=stats.get("failed", 0),
                partial=stats.get("partial", 0),
            )
        except Exception:
            logger.warning("dashboard_hook_executions_summary_failed", exc_info=True)
            return HookExecutionsSummary()

    async def _get_webhook_deliveries_summary(
        self, start: datetime, end: datetime
    ) -> WebhookDeliveriesSummary:
        """Get webhook delivery outcomes for the selected range."""
        try:
            stats = await self.webhook_delivery_repo.count_by_status_between(start, end)
            return WebhookDeliveriesSummary(
                delivered=stats.get("delivered", 0),
                failed=stats.get("failed", 0),
                pending=stats.get("pending", 0),
                retrying=stats.get("retrying", 0),
            )
        except Exception:
            logger.warning(
                "dashboard_webhook_deliveries_summary_failed",
                exc_info=True,
            )
            return WebhookDeliveriesSummary()

    def _zero_fill_series(
        self,
        buckets: list[tuple[str, int]],
        days: int,
        end: datetime,
    ) -> list[TimeSeriesPoint]:
        """Build a continuous daily series of exact length with zeros for missing days.

        Produces ``days`` points ending on ``end``'s UTC calendar day (inclusive),
        ordered ascending by date.

        Args:
            buckets: Sparse (YYYY-MM-DD, count) pairs from the repository.
            days: Number of calendar days to include (7, 30, or 90).
            end: Reference datetime (typically now); last series day is end.date().

        Returns:
            Zero-filled list of TimeSeriesPoint of length ``days``.
        """
        counts = {day: count for day, count in buckets}
        end_day = end.date() if isinstance(end, datetime) else end
        start_day = end_day - timedelta(days=days - 1)

        points: list[TimeSeriesPoint] = []
        current = start_day
        while current <= end_day:
            key = current.isoformat()
            points.append(TimeSeriesPoint(date=key, count=counts.get(key, 0)))
            current += timedelta(days=1)
        return points

    def _zero_fill_audit_series(
        self,
        buckets: list[tuple[str, str, int]],
        days: int,
        end: datetime,
    ) -> list[AuditOperationPoint]:
        """Build a continuous daily audit series with create/update/delete counts.

        Args:
            buckets: Sparse (YYYY-MM-DD, operation, count) triples from the repository.
            days: Number of calendar days to include (7, 30, or 90).
            end: Reference datetime (typically now); last series day is end.date().

        Returns:
            Zero-filled list of AuditOperationPoint of length ``days``.
        """
        by_day: dict[str, dict[str, int]] = {}
        for day, operation, count in buckets:
            op = operation.upper()
            if day not in by_day:
                by_day[day] = {"create": 0, "update": 0, "delete": 0}
            if op == "CREATE":
                by_day[day]["create"] += count
            elif op == "UPDATE":
                by_day[day]["update"] += count
            elif op == "DELETE":
                by_day[day]["delete"] += count

        end_day = end.date() if isinstance(end, datetime) else end
        start_day = end_day - timedelta(days=days - 1)

        points: list[AuditOperationPoint] = []
        current = start_day
        while current <= end_day:
            key = current.isoformat()
            day_counts = by_day.get(key, {"create": 0, "update": 0, "delete": 0})
            points.append(
                AuditOperationPoint(
                    date=key,
                    create=day_counts["create"],
                    update=day_counts["update"],
                    delete=day_counts["delete"],
                )
            )
            current += timedelta(days=1)
        return points

    async def _count_records_by_collection(
        self, top_n: int = 10
    ) -> tuple[int, list[CollectionRecordCount]]:
        """Count records across all dynamic collection tables.

        Uses a single batched ``UNION ALL`` of ``COUNT(*)`` statements when
        possible (O(1) round-trips vs N). Falls back to per-table sequential
        counts if the batch query fails (e.g. missing tables).

        Returns total count and a ranked top-N list (plus optional Other bucket).
        Missing tables are skipped so one bad collection cannot fail the dashboard.

        Args:
            top_n: Maximum number of named collections to include before Other.

        Returns:
            Tuple of (total_records, records_by_collection).
        """
        collections = await self.session.execute(text("SELECT name FROM collections"))
        collection_names = [row[0] for row in collections.fetchall()]

        if not collection_names:
            return 0, []

        counts = await self._count_collection_tables(collection_names)
        total = sum(c for _, c in counts)

        counts.sort(key=lambda item: item[1], reverse=True)
        top = counts[:top_n]
        remainder = sum(c for _, c in counts[top_n:])

        records_by_collection = [
            CollectionRecordCount(name=name, count=count) for name, count in top
        ]
        if remainder > 0:
            records_by_collection.append(
                CollectionRecordCount(name="Other", count=remainder)
            )

        return total, records_by_collection

    def _collection_table_name(self, collection_name: str) -> str | None:
        """Map a collection name to a safe physical table identifier.

        Returns None if the generated name is not a safe SQL identifier.
        """
        table_name = TableBuilder.generate_table_name(collection_name)
        if not _COLLECTION_TABLE_RE.match(table_name):
            return None
        return table_name

    async def _count_collection_tables(
        self, collection_names: list[str]
    ) -> list[tuple[str, int]]:
        """Count rows per collection table (batched UNION ALL with sequential fallback).

        Args:
            collection_names: Logical collection names from the collections table.

        Returns:
            List of (collection_name, count) for tables that could be counted.
        """
        segments: list[str] = []
        for name in collection_names:
            table_name = self._collection_table_name(name)
            if table_name is None:
                continue
            # Collection name as a string literal (escape single quotes).
            safe_name = str(name).replace("'", "''")
            segments.append(
                f"SELECT '{safe_name}' AS name, COUNT(*) AS count "
                f'FROM "{table_name}"'
            )

        if not segments:
            return []

        sql = " UNION ALL ".join(segments)
        try:
            result = await self.session.execute(text(sql))
            rows = result.fetchall()
            return [(str(row[0]), int(row[1] or 0)) for row in rows]
        except Exception:
            # One missing table can fail the whole UNION; degrade to sequential.
            logger.warning(
                "dashboard_batch_record_count_failed",
                collection_count=len(collection_names),
                exc_info=True,
            )
            return await self._sequential_count_collection_tables(collection_names)

    async def _sequential_count_collection_tables(
        self, collection_names: list[str]
    ) -> list[tuple[str, int]]:
        """Count each collection table individually, skipping missing tables.

        Args:
            collection_names: Logical collection names.

        Returns:
            List of (collection_name, count) for successful counts.
        """
        counts: list[tuple[str, int]] = []
        for collection_name in collection_names:
            table_name = self._collection_table_name(collection_name)
            if table_name is None:
                continue
            try:
                result = await self.session.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                )
                count = int(result.scalar_one() or 0)
                counts.append((collection_name, count))
            except Exception:
                # Table might not exist or other error; skip without failing
                continue
        return counts

    async def _count_total_records(self) -> int:
        """Count total records across all dynamic collection tables.

        Returns:
            Total count of records.
        """
        total, _ = await self._count_records_by_collection()
        return total

    async def _get_system_health(self) -> SystemHealthStats:
        """Get system health statistics.

        Returns:
            SystemHealthStats with database and storage info.
        """
        # Check database connection
        try:
            await self.session.execute(text("SELECT 1"))
            database_status = "connected"
        except Exception:
            database_status = "disconnected"

        # Get storage usage
        storage_usage_mb = self._get_storage_usage()

        return SystemHealthStats(
            database_status=database_status,
            storage_usage_mb=storage_usage_mb,
        )

    def _get_storage_usage(self) -> float:
        """Get storage usage in MB.

        Returns:
            Storage usage in megabytes.
        """
        settings = get_settings()
        storage_path = Path(settings.storage_path)

        if not storage_path.exists():
            return 0.0

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(storage_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)

        # Convert bytes to MB
        return round(total_size / (1024 * 1024), 2)
