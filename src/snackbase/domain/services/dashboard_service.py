"""Dashboard service for aggregating statistics.

Provides methods for collecting and aggregating dashboard metrics
from various repositories.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.domain.services.audit_log_service import AuditLogService
from snackbase.infrastructure.api.schemas import (
    AuditLogResponse,
    AuditOperationPoint,
    CollectionRecordCount,
    DashboardStats,
    PreviousPeriodStats,
    RecentRegistration,
    SystemHealthStats,
    TimeSeriesPoint,
    TimeSeriesStats,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    CollectionRepository,
    RefreshTokenRepository,
    UserRepository,
)
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)
from snackbase.infrastructure.persistence.repositories.collection_rule_repository import (
    CollectionRuleRepository,
)

DashboardRange = Literal["7d", "30d", "90d"]

RANGE_DAYS: dict[DashboardRange, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}


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
        now = datetime.now(timezone.utc)
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
            recent_audit_logs=recent_audit_logs,
        )

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

        Returns total count and a ranked top-N list (plus optional Other bucket).
        Missing tables are skipped so one bad collection cannot fail the dashboard.

        Args:
            top_n: Maximum number of named collections to include before Other.

        Returns:
            Tuple of (total_records, records_by_collection).
        """
        collections = await self.session.execute(text("SELECT name FROM collections"))
        collection_names = [row[0] for row in collections.fetchall()]

        counts: list[tuple[str, int]] = []
        total = 0
        for collection_name in collection_names:
            table_name = f"col_{collection_name.lower().replace(' ', '_')}"
            try:
                result = await self.session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                count = int(result.scalar_one() or 0)
                total += count
                counts.append((collection_name, count))
            except Exception:
                # Table might not exist or other error; skip without failing
                continue

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
