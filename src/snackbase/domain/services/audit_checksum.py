"""Audit checksum utility.

This module provides a shared implementation for calculating audit log checksums
to ensure consistency between the async AuditLogRepository and the synchronous
SyncAuditLogRepository.
"""

import hashlib
import json
from datetime import datetime
from typing import Any


class AuditChecksum:
    """Utility for calculating audit log integrity checksums."""

    @staticmethod
    def calculate(
        account_id: str,
        operation: str,
        table_name: str,
        record_id: str,
        column_name: str,
        old_value: str | None,
        new_value: str | None,
        user_id: str,
        user_email: str,
        user_name: str,
        es_username: str | None,
        es_reason: str | None,
        es_timestamp: datetime | None,
        ip_address: str | None,
        user_agent: str | None,
        request_id: str | None,
        occurred_at: datetime,
        previous_hash: str | None,
        extra_metadata: dict[str, Any] | None,
    ) -> str:
        """Calculate SHA-256 checksum for an audit log entry.

        Args:
            account_id: Account ID.
            operation: Operation type (CREATE, UPDATE, DELETE).
            table_name: Table name.
            record_id: Record ID.
            column_name: Column name.
            old_value: Old value.
            new_value: New value.
            user_id: User ID.
            user_email: User email.
            user_name: User name.
            es_username: Electronic signature username.
            es_reason: Electronic signature reason.
            es_timestamp: Electronic signature timestamp.
            ip_address: IP address.
            user_agent: User agent.
            request_id: Request ID.
            occurred_at: Occurrence timestamp.
            previous_hash: Hash of the previous entry.
            extra_metadata: Extra metadata dictionary.

        Returns:
            SHA-256 checksum as a hexadecimal string.
        """
        # Helper to normalize datetime - remove timezone info for consistent hashing
        # mimicking the logic originally in AuditLogRepository
        def normalize_dt(dt: datetime | None) -> str | None:
            if dt is None:
                return None
            if hasattr(dt, 'replace') and dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt.isoformat() if dt else None

        # Build a dictionary of all fields to hash
        data = {
            "account_id": account_id,
            "operation": operation,
            "table_name": table_name,
            "record_id": record_id,
            "column_name": column_name,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id,
            "user_email": user_email,
            "user_name": user_name,
            "es_username": es_username,
            "es_reason": es_reason,
            "es_timestamp": normalize_dt(es_timestamp),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "occurred_at": normalize_dt(occurred_at),
            "previous_hash": previous_hash,
            "extra_metadata": extra_metadata,
        }

        # Convert to JSON string (sorted keys for consistency)
        json_str = json.dumps(data, sort_keys=True, default=str)

        # Calculate SHA-256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
