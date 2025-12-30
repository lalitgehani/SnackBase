"""Audit log entity for GxP-compliant audit trail.

This entity represents a single audit log entry with column-level granularity.
Each entry is immutable and part of a blockchain-style integrity chain.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditLog:
    """Audit log entity for tracking data changes.

    Represents a single column change in the audit trail. Multiple AuditLog
    entries are created for operations that affect multiple columns.

    Attributes:
        id: Unique identifier (auto-generated).
        account_id: Account context for the change.
        operation: Type of operation (CREATE, UPDATE, DELETE).
        table_name: Name of the table/collection affected.
        record_id: ID of the record that was changed.
        column_name: Name of the column that was changed.
        old_value: Previous value (NULL for CREATE).
        new_value: New value (NULL for DELETE).
        user_id: ID of the user who made the change.
        user_email: Email of the user who made the change.
        user_name: Name of the user who made the change.
        es_username: Electronic signature username (CFR Part 11).
        es_reason: Electronic signature reason (CFR Part 11).
        es_timestamp: Electronic signature timestamp (CFR Part 11).
        ip_address: IP address of the client.
        user_agent: User agent string from the request.
        request_id: Correlation ID for the request.
        occurred_at: Timestamp when the change occurred (UTC).
        checksum: SHA-256 hash of this audit entry.
        previous_hash: Checksum of the previous audit entry (blockchain chain).
        extra_metadata: Additional metadata as JSON (extensible).
    """

    # Core identification
    id: int | None = None
    account_id: str = ""
    operation: str = ""  # CREATE, UPDATE, DELETE
    table_name: str = ""
    record_id: str = ""
    column_name: str = ""

    # Value tracking
    old_value: str | None = None
    new_value: str | None = None

    # User context
    user_id: str = ""
    user_email: str = ""
    user_name: str = ""

    # Electronic signature (CFR Part 11)
    es_username: str | None = None
    es_reason: str | None = None
    es_timestamp: datetime | None = None

    # Request metadata
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None

    # Timing and integrity
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checksum: str | None = None
    previous_hash: str | None = None

    # Additional data
    extra_metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate audit log data after initialization."""
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.operation:
            raise ValueError("Operation is required")
        if self.operation not in ("CREATE", "UPDATE", "DELETE"):
            raise ValueError(f"Invalid operation: {self.operation}")
        if not self.table_name:
            raise ValueError("Table name is required")
        if not self.record_id:
            raise ValueError("Record ID is required")
        if not self.column_name:
            raise ValueError("Column name is required")
        if not self.user_id:
            raise ValueError("User ID is required")
        if not self.user_email:
            raise ValueError("User email is required")
