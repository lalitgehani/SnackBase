"""Dashboard service for aggregating statistics.

Provides methods for collecting and aggregating dashboard metrics
from various repositories.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.api.schemas import (
    AuditLogResponse,
    DashboardStats,
    RecentRegistration,
    SystemHealthStats,
)
from snackbase.domain.services.audit_log_service import AuditLogService
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    CollectionRepository,
    RefreshTokenRepository,
    UserRepository,
)


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
        self.refresh_token_repo = RefreshTokenRepository(session)
        self.audit_log_service = AuditLogService(session)

    async def get_dashboard_stats(self, user_groups: list[str]) -> DashboardStats:
        """Get all dashboard statistics.

        Args:
            user_groups: List of group names the user belongs to for PII masking.

        Returns:
            DashboardStats with all metrics populated.
        """
        # Calculate 7 days ago for time-based metrics
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # Get total counts
        total_accounts = await self.account_repo.count_all()
        total_users = await self.user_repo.count_all()
        total_collections = await self.collection_repo.count_all()
        total_records = await self._count_total_records()

        # Get growth metrics (last 7 days)
        new_accounts_7d = await self.account_repo.count_created_since(seven_days_ago)
        new_users_7d = await self.user_repo.count_created_since(seven_days_ago)

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

        # Get active sessions count
        active_sessions = await self.refresh_token_repo.count_active_sessions()

        # Get recent audit logs (last 20) - with PII masking (returns dicts)
        logs, _ = await self.audit_log_service.list_logs(limit=20, sort_by="occurred_at", sort_order="desc")
        masked_logs = self.audit_log_service.mask_for_display(logs, user_groups)
        recent_audit_logs = [
            AuditLogResponse(**log)
            for log in masked_logs
        ]

        return DashboardStats(
            total_accounts=total_accounts,
            total_users=total_users,
            total_collections=total_collections,
            total_records=total_records,
            new_accounts_7d=new_accounts_7d,
            new_users_7d=new_users_7d,
            recent_registrations=recent_registrations,
            system_health=system_health,
            active_sessions=active_sessions,
            recent_audit_logs=recent_audit_logs,
        )

    async def _count_total_records(self) -> int:
        """Count total records across all dynamic collection tables.

        Returns:
            Total count of records.
        """
        # Get all collections
        collections = await self.session.execute(
            text("SELECT name FROM collections")
        )
        collection_names = [row[0] for row in collections.fetchall()]

        total = 0
        for collection_name in collection_names:
            # Generate table name (same logic as TableBuilder)
            table_name = f"col_{collection_name.lower().replace(' ', '_')}"
            try:
                result = await self.session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                count = result.scalar_one()
                total += count
            except Exception:
                # Table might not exist or other error, skip
                continue

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
