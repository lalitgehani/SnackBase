"""Dashboard API schemas.

Pydantic schemas for dashboard statistics and metrics.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    account_code: str = Field(..., description="Human-readable account code in XX#### format (e.g., AB1234)")
    account_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogEntry(BaseModel):
    """Audit log entry (placeholder for F3.7)."""

    id: str
    operation: str
    table_name: str
    user_email: str
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    # Total counts
    total_accounts: int
    total_users: int
    total_collections: int
    total_records: int

    # Growth metrics (last 7 days)
    new_accounts_7d: int
    new_users_7d: int

    # Recent activity
    recent_registrations: list[RecentRegistration]

    # System health
    system_health: SystemHealthStats

    # Active sessions
    active_sessions: int

    # Audit logs (placeholder until F3.7)
    recent_audit_logs: list[AuditLogEntry]

    model_config = ConfigDict(from_attributes=True)
