"""Audit log repository for write-only audit trail operations.

This repository provides methods to create audit log entries with automatic
integrity chain management (checksums and previous_hash linking).
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel


class AuditLogRepository:
    """Repository for audit log database operations.

    This repository is write-only - it only supports creating audit log entries.
    UPDATE and DELETE operations are intentionally not provided to enforce
    immutability of the audit trail.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, audit_log: AuditLogModel) -> AuditLogModel:
        """Create a new audit log entry with automatic integrity chain.

        This method automatically:
        - Retrieves the previous audit log entry's checksum
        - Sets the previous_hash to link to the previous entry
        - Calculates the SHA-256 checksum for this entry
        - Assigns the next sequence number

        Args:
            audit_log: Audit log model to create (without checksum/previous_hash).

        Returns:
            Created audit log model with checksum and previous_hash set.
        """
        # Get the previous audit log entry's checksum
        previous_hash = await self._get_latest_checksum()
        audit_log.previous_hash = previous_hash

        # Calculate checksum for this entry
        # Note: We normalize the datetime to remove timezone since SQLite stores without tz
        audit_log.checksum = self._calculate_checksum(audit_log)

        # Add to session and flush to get the auto-generated fields
        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)

        return audit_log

    async def create_batch(
        self, audit_logs: list[AuditLogModel]
    ) -> list[AuditLogModel]:
        """Create multiple audit log entries efficiently.

        This method creates multiple audit log entries in a single transaction,
        maintaining the integrity chain across all entries.

        Args:
            audit_logs: List of audit log models to create.

        Returns:
            List of created audit log models with checksums and hashes set.
        """
        if not audit_logs:
            return []

        # Get the previous audit log entry's checksum
        previous_hash = await self._get_latest_checksum()

        # Process each audit log entry
        for audit_log in audit_logs:
            audit_log.previous_hash = previous_hash
            audit_log.checksum = self._calculate_checksum(audit_log)

            # Add to session
            self.session.add(audit_log)

            # Update previous_hash for the next entry in the batch
            previous_hash = audit_log.checksum

        # Flush to get auto-generated fields
        await self.session.flush()

        # Refresh all entries to get the final state
        for audit_log in audit_logs:
            await self.session.refresh(audit_log)

        return audit_logs

    async def _get_latest_checksum(self) -> str | None:
        """Get the checksum of the most recent audit log entry.

        Returns:
            Checksum of the latest entry, or None if no entries exist.
        """
        result = await self.session.execute(
            select(AuditLogModel.checksum)
            .order_by(AuditLogModel.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _calculate_checksum(self, audit_log: AuditLogModel) -> str:
        """Calculate SHA-256 checksum for an audit log entry.

        The checksum is calculated from all relevant fields to ensure
        integrity of the audit trail. Datetime values are normalized
        to remove timezone info since SQLite stores datetimes without timezone.

        Args:
            audit_log: Audit log model to calculate checksum for.

        Returns:
            SHA-256 checksum as a hexadecimal string.
        """
        # Helper to normalize datetime - remove timezone info for consistent hashing
        def normalize_dt(dt):
            if dt is None:
                return None
            if hasattr(dt, 'replace') and dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt.isoformat() if dt else None

        # Build a dictionary of all fields to hash
        data = {
            "account_id": audit_log.account_id,
            "operation": audit_log.operation,
            "table_name": audit_log.table_name,
            "record_id": audit_log.record_id,
            "column_name": audit_log.column_name,
            "old_value": audit_log.old_value,
            "new_value": audit_log.new_value,
            "user_id": audit_log.user_id,
            "user_email": audit_log.user_email,
            "user_name": audit_log.user_name,
            "es_username": audit_log.es_username,
            "es_reason": audit_log.es_reason,
            "es_timestamp": normalize_dt(audit_log.es_timestamp),
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent,
            "request_id": audit_log.request_id,
            "occurred_at": normalize_dt(audit_log.occurred_at),
            "previous_hash": audit_log.previous_hash,
            "extra_metadata": audit_log.extra_metadata,
        }

        # Convert to JSON string (sorted keys for consistency)
        json_str = json.dumps(data, sort_keys=True, default=str)

        # Calculate SHA-256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    async def count_all(self) -> int:
        """Count total number of audit log entries.

        Returns:
            Total count of audit log entries.
        """
        result = await self.session.execute(select(func.count(AuditLogModel.id)))
        return result.scalar_one() or 0

    async def verify_integrity_chain(self) -> tuple[bool, list[str]]:
        """Verify the integrity of the audit log chain.

        Checks that:
        1. Each entry's checksum is valid
        2. Each entry's previous_hash matches the previous entry's checksum

        Returns:
            Tuple of (is_valid, list_of_errors).
            If is_valid is True, list_of_errors will be empty.
        """
        errors = []

        # Get all audit log entries ordered by id (which serves as sequence number)
        result = await self.session.execute(
            select(AuditLogModel).order_by(AuditLogModel.id.asc())
        )
        entries = list(result.scalars().all())

        if not entries:
            return True, []

        previous_checksum = None

        for entry in entries:
            # Verify checksum
            calculated_checksum = self._calculate_checksum(entry)
            if entry.checksum != calculated_checksum:
                errors.append(
                    f"Entry {entry.id}: "
                    f"Checksum mismatch. Expected {calculated_checksum}, "
                    f"got {entry.checksum}"
                )

            # Verify previous_hash chain
            if entry.previous_hash != previous_checksum:
                errors.append(
                    f"Entry {entry.id}: "
                    f"Previous hash mismatch. Expected {previous_checksum}, "
                    f"got {entry.previous_hash}"
                )

            previous_checksum = entry.checksum

        return len(errors) == 0, errors
