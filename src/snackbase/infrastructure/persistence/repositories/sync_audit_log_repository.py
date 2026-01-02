"""Synchronous Audit Log Repository.

This repository provides synchronous methods to create audit log entries using
an existing SQLAlchemy Connection. This is required for creating audit logs
triggerd by SQLAlchemy event listeners within the same transaction to avoid
locking issues (especially with SQLite).
"""

from typing import Any, List, Optional
from datetime import datetime, timezone

from sqlalchemy import insert, select, func, text, desc
from sqlalchemy.engine import Connection

from snackbase.domain.services.audit_checksum import AuditChecksum
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel


class SyncAuditLogRepository:
    """Synchronous repository for audit log operations using SQLAlchemy Core."""

    def __init__(self, connection: Connection) -> None:
        """Initialize with a synchronous SQLAlchemy Connection.

        Args:
            connection: Active SQLAlchemy connection (inside a transaction).
        """
        self.connection = connection

    def create_batch(self, audit_entries_data: List[dict[str, Any]]) -> None:
        """Create multiple audit log entries synchronously.

        Args:
            audit_entries_data: List of dictionaries containing audit log data.
                                Keys must match AuditLogModel columns.
        """
        if not audit_entries_data:
            return

        # Get the previous checksum
        previous_hash = self._get_latest_checksum()

        # Process each entry to add checksum and integrity chain
        for entry in audit_entries_data:
            entry["previous_hash"] = previous_hash
            
            # Ensure timestamps are set if not present
            if "occurred_at" not in entry or entry["occurred_at"] is None:
                entry["occurred_at"] = datetime.now(timezone.utc)
                
            # Calculate checksum
            checksum = AuditChecksum.calculate(
                account_id=entry.get("account_id"),
                operation=entry.get("operation"),
                table_name=entry.get("table_name"),
                record_id=entry.get("record_id"),
                column_name=entry.get("column_name"),
                old_value=entry.get("old_value"),
                new_value=entry.get("new_value"),
                user_id=entry.get("user_id"),
                user_email=entry.get("user_email"),
                user_name=entry.get("user_name"),
                es_username=entry.get("es_username"),
                es_reason=entry.get("es_reason"),
                es_timestamp=entry.get("es_timestamp"),
                ip_address=entry.get("ip_address"),
                user_agent=entry.get("user_agent"),
                request_id=entry.get("request_id"),
                occurred_at=entry.get("occurred_at"),
                previous_hash=previous_hash,
                extra_metadata=entry.get("extra_metadata"),
            )
            
            entry["checksum"] = checksum
            previous_hash = checksum

        # Execute batch insert using Core
        stmt = insert(AuditLogModel)
        self.connection.execute(stmt, audit_entries_data)

    def _get_latest_checksum(self) -> Optional[str]:
        """Get the checksum of the most recent audit log entry synchronously.

        Returns:
            Checksum of the latest entry, or None if no entries exist.
        """
        stmt = select(AuditLogModel.checksum).order_by(AuditLogModel.id.desc()).limit(1)
        result = self.connection.execute(stmt)
        return result.scalar_one_or_none()
