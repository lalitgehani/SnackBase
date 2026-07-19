"""Dashboard API schemas.

Pydantic schemas for dashboard statistics and metrics.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from snackbase.infrastructure.api.schemas.audit_log_schemas import AuditLogResponse

DashboardRange = Literal["7d", "30d", "90d"]


class SystemHealthStats(BaseModel):
    """System health statistics."""

    database_status: str
    storage_usage_mb: float

    model_config = ConfigDict(from_attributes=True)


class RecentRegistration(BaseModel):
    """Recent user registration information."""

    id: str
    email: str
    account_id: str = Field(..., description="Account ID (UUID)")
    account_code: str = Field(
        ..., description="Human-readable account code in XX#### format (e.g., AB1234)"
    )
    account_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesPoint(BaseModel):
    """Single day bucket in a growth time series."""

    date: str = Field(..., description="Calendar day in YYYY-MM-DD (UTC)")
    count: int = Field(..., description="Number of entities created on this day")

    model_config = ConfigDict(from_attributes=True)


class AuditOperationPoint(BaseModel):
    """Daily audit log volume broken down by operation type."""

    date: str = Field(..., description="Calendar day in YYYY-MM-DD (UTC)")
    create: int = Field(0, description="CREATE operation row count for this day")
    update: int = Field(0, description="UPDATE operation row count for this day")
    delete: int = Field(0, description="DELETE operation row count for this day")

    model_config = ConfigDict(from_attributes=True)


class CollectionRecordCount(BaseModel):
    """Record count for a single collection (or the Other bucket)."""

    name: str = Field(..., description="Collection name, or 'Other' for remainder")
    count: int = Field(..., description="Number of rows in the collection table")

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesStats(BaseModel):
    """Daily growth series for the selected range."""

    accounts_created: list[TimeSeriesPoint] = Field(
        default_factory=list,
        description="New accounts per day in the selected range (zero-filled)",
    )
    users_created: list[TimeSeriesPoint] = Field(
        default_factory=list,
        description="New users per day in the selected range (zero-filled)",
    )
    audit_by_operation: list[AuditOperationPoint] = Field(
        default_factory=list,
        description="Audit log volume by CREATE/UPDATE/DELETE per day (zero-filled)",
    )

    model_config = ConfigDict(from_attributes=True)


class PreviousPeriodStats(BaseModel):
    """Growth counts for the equal-length period immediately before the selected range."""

    new_accounts: int = Field(..., description="Accounts created in the previous period")
    new_users: int = Field(..., description="Users created in the previous period")

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    # Total counts
    total_accounts: int
    total_users: int
    total_collections: int
    total_records: int

    # Growth metrics for the selected range (field names kept for compatibility;
    # values always reflect the effective `range`, not necessarily calendar 7 days).
    new_accounts_7d: int = Field(
        ...,
        description="New accounts in the selected range (name kept for backward compatibility)",
    )
    new_users_7d: int = Field(
        ...,
        description="New users in the selected range (name kept for backward compatibility)",
    )

    # Effective time range for range-scoped metrics
    range: DashboardRange = Field(
        default="7d",
        description="Effective time range used for growth metrics and time series",
    )

    # Previous period of equal length immediately before the selected range
    previous_period: PreviousPeriodStats

    # Daily growth series (zero-filled for missing days)
    time_series: TimeSeriesStats

    # Recent activity
    recent_registrations: list[RecentRegistration]

    # System health
    system_health: SystemHealthStats

    # Active sessions
    active_sessions: int

    # Public collections count
    public_collections_count: int = Field(
        default=0, description="Collections with at least one public rule"
    )

    # Top collections by record count (descending); may include an "Other" bucket
    records_by_collection: list[CollectionRecordCount] = Field(
        default_factory=list,
        description="Top collections by row count (default top 10 + optional Other)",
    )

    # Audit logs
    recent_audit_logs: list[AuditLogResponse]

    model_config = ConfigDict(from_attributes=True)
