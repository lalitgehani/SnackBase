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


class FeatureCounts(BaseModel):
    """Platform feature adoption counts (global, not range-scoped)."""

    hooks: int = Field(0, description="Total hooks across all accounts")
    hooks_enabled: int = Field(0, description="Enabled hooks")
    webhooks: int = Field(0, description="Total webhooks across all accounts")
    webhooks_enabled: int = Field(0, description="Enabled webhooks")
    workflows: int = Field(0, description="Total workflows")
    endpoints: int = Field(0, description="Total custom endpoints")
    macros: int = Field(0, description="Total SQL macros")
    api_keys_active: int = Field(0, description="Active (non-revoked) API keys")
    invitations_pending: int = Field(
        0, description="Pending invitations (not accepted, not expired)"
    )

    model_config = ConfigDict(from_attributes=True)


class JobsByStatus(BaseModel):
    """Live job queue composition (current snapshot, not range-scoped)."""

    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    retrying: int = 0
    dead: int = 0

    model_config = ConfigDict(from_attributes=True)


class HookExecutionsSummary(BaseModel):
    """Hook execution outcomes for the selected time range (via executed_at)."""

    success: int = 0
    failed: int = 0
    partial: int = 0

    model_config = ConfigDict(from_attributes=True)


class WebhookDeliveriesSummary(BaseModel):
    """Webhook delivery outcomes for the selected time range (via created_at)."""

    delivered: int = 0
    failed: int = 0
    pending: int = 0
    retrying: int = 0

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

    # Phase 3: automation and integrations health
    feature_counts: FeatureCounts = Field(
        default_factory=FeatureCounts,
        description="Platform feature adoption counts",
    )
    jobs_by_status: JobsByStatus = Field(
        default_factory=JobsByStatus,
        description="Live job queue composition by status",
    )
    hook_executions_summary: HookExecutionsSummary = Field(
        default_factory=HookExecutionsSummary,
        description="Hook execution outcomes in the selected range",
    )
    webhook_deliveries_summary: WebhookDeliveriesSummary = Field(
        default_factory=WebhookDeliveriesSummary,
        description="Webhook delivery outcomes in the selected range",
    )

    # Audit logs
    recent_audit_logs: list[AuditLogResponse]

    model_config = ConfigDict(from_attributes=True)
