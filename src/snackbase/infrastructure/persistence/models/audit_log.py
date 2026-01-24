"""SQLAlchemy model for the audit_log table.

This table stores GxP-compliant audit trails for all data changes.
Entries are immutable (write-once) and form a blockchain-style integrity chain.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class AuditLogModel(Base):
    """SQLAlchemy model for the audit_log table.

    This table stores audit trails with column-level granularity. Each row
    represents a single column change. Multiple rows are created for operations
    that affect multiple columns.

    The table is immutable - UPDATE and DELETE operations are prevented by
    database triggers to ensure audit trail integrity.

    Attributes:
        id: Primary key (auto-incrementing, serves as sequence number).
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

    __tablename__ = "audit_log"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier",
    )

    # Core identification
    account_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Account context (UUID)",
    )
    operation: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Operation type: CREATE, UPDATE, DELETE",
    )
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Table/collection name",
    )
    record_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="ID of the affected record",
    )
    column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of the changed column",
    )

    # Value tracking
    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Previous value (NULL for CREATE)",
    )
    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="New value (NULL for DELETE)",
    )

    # User context
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="ID of user who made the change",
    )
    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email of user who made the change",
    )
    user_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of user who made the change",
    )

    # Electronic signature (CFR Part 11)
    es_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Electronic signature username",
    )
    es_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Electronic signature reason",
    )
    es_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Electronic signature timestamp",
    )

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="User agent string from request",
    )
    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="Correlation ID for the request",
    )

    # Timing and integrity
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp when the change occurred (UTC)",
    )
    checksum: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of this audit entry",
    )
    previous_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Checksum of the previous audit entry (blockchain chain)",
    )

    # Additional data
    extra_metadata: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Additional metadata as JSON",
    )

    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_audit_log_account_table", "account_id", "table_name"),
        Index("ix_audit_log_table_record", "table_name", "record_id"),
        Index("ix_audit_log_occurred_at_desc", occurred_at.desc()),
        # Validate operation values
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_audit_log_operation",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, operation={self.operation}, "
            f"table={self.table_name}, record={self.record_id}, "
            f"column={self.column_name})>"
        )


# Database triggers to prevent UPDATE and DELETE operations
# These ensure the audit log is truly immutable


@event.listens_for(AuditLogModel.__table__, "after_create")
def create_immutability_triggers(target, connection, **kw):
    """Create database triggers to prevent UPDATE and DELETE on audit_log.

    These triggers enforce immutability at the database level, ensuring
    that audit log entries cannot be modified or deleted once written.
    """
    # Only create triggers for SQLite
    # For PostgreSQL, we would use different syntax
    if connection.dialect.name == "sqlite":
        # Trigger to prevent UPDATE
        connection.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
                BEFORE UPDATE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be updated');
                END;
                """
            )
        )

        # Trigger to prevent DELETE
        connection.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
                BEFORE DELETE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be deleted');
                END;
                """
            )
        )


# Import text for the trigger creation
from sqlalchemy import text  # noqa: E402
