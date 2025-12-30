"""Pydantic schemas for audit log endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class AuditLogResponse(BaseModel):
    """Response for a single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier (sequence number)")
    account_id: str = Field(..., description="Account context (UUID)")
    operation: str = Field(..., description="Operation type: CREATE, UPDATE, DELETE")
    table_name: str = Field(..., description="Table/collection name")
    record_id: str = Field(..., description="ID of the affected record")
    column_name: str = Field(..., description="Name of the changed column")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: Optional[str] = Field(None, description="New value")
    user_id: str = Field(..., description="ID of user who made the change")
    user_email: str = Field(..., description="Email of user who made the change")
    user_name: str = Field(..., description="Name of user who made the change")
    es_username: Optional[str] = Field(None, description="Electronic signature username")
    es_reason: Optional[str] = Field(None, description="Electronic signature reason")
    es_timestamp: Optional[datetime] = Field(None, description="Electronic signature timestamp")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    request_id: Optional[str] = Field(None, description="Correlation ID")
    occurred_at: datetime = Field(..., description="Timestamp of the change (UTC)")
    checksum: Optional[str] = Field(None, description="SHA-256 hash of this entry")
    previous_hash: Optional[str] = Field(None, description="Checksum of the previous entry")
    extra_metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class AuditLogListResponse(BaseModel):
    """Response for listing audit logs."""

    items: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of entries matching filters")
    skip: int = Field(..., description="Number of entries skipped")
    limit: int = Field(..., description="Number of entries returned")


class AuditLogExportFormat(str, Enum):
    """Available export formats for audit logs."""

    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
