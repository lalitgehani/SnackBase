"""Audit log service for capturing data changes.

This service handles the automatic capture of audit log entries for all
CREATE, UPDATE, DELETE operations with column-level granularity.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect

from snackbase.core.logging import get_logger
from snackbase.domain.entities.audit_log import AuditLog
from snackbase.domain.services.pii_masking_service import PIIMaskingService
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)

logger = get_logger(__name__)


class AuditLogService:
    """Service for capturing audit log entries.

    This service extracts column-level changes from SQLAlchemy models and
    creates audit log entries with user context and request metadata.
    """

    # Tables that should not be audited
    EXCLUDED_TABLES = {
        "audit_log",  # Don't audit the audit log itself
        "alembic_version",  # Don't audit migration tracking
        "refresh_tokens",  # High-volume tokens
        "oauth_states",  # Temporary flow state
    }

    # Fields that should always be masked (e.g., secrets, tokens)
    SENSITIVE_FIELDS = {
        "password",
        "password_hash",
        "hashed_password",
        "refresh_token",
        "token_hash",
        "access_token",
        "client_secret",
        "secret",
        "code_verifier",
        "state_token",
        "verification_token",
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the audit log service.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.repository = AuditLogRepository(session)

    async def capture_create(
        self,
        model: Any,
        user_id: str,
        user_email: str,
        user_name: str,
        account_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Capture audit log entries for a CREATE operation.

        Creates one audit log entry per column with old_value=NULL.
        Stores raw data in database (except passwords which are always masked).

        Args:
            model: SQLAlchemy model instance that was created.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
            extra_metadata: Additional metadata to store.
        """
        try:
            table_name = model.__tablename__
            
            # Skip excluded tables
            if self._should_skip_table(table_name):
                return

            # Get record ID
            record_id = self._get_record_id(model)
            if not record_id:
                logger.warning(
                    f"Cannot audit CREATE for {table_name}: no record ID found"
                )
                return

            # Extract all columns and their values
            columns = self._extract_columns(model)
            
            # Create audit entries
            audit_entries = []
            occurred_at = datetime.now(timezone.utc)
            
            for column_name, new_value in columns.items():
                # Only mask sensitive fields (security requirement), store everything else as-is
                masked_value = self.mask_sensitive_only(column_name, new_value)

                audit_entry = AuditLogModel(
                    account_id=account_id,
                    operation="CREATE",
                    table_name=table_name,
                    record_id=record_id,
                    column_name=column_name,
                    old_value=None,  # NULL for CREATE
                    new_value=masked_value,
                    user_id=user_id,
                    user_email=user_email,
                    user_name=user_name,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    extra_metadata=extra_metadata,
                )
                audit_entries.append(audit_entry)
            
            # Batch create audit entries
            if audit_entries:
                await self.repository.create_batch(audit_entries)
                logger.debug(
                    f"Captured {len(audit_entries)} audit entries for CREATE {table_name}",
                    record_id=record_id,
                )
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(
                f"Failed to capture audit log for CREATE {model.__tablename__}",
                error=str(e),
                exc_info=True,
            )

    async def capture_update(
        self,
        model: Any,
        old_values: dict[str, Any],
        user_id: str,
        user_email: str,
        user_name: str,
        account_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Capture audit log entries for an UPDATE operation.

        Creates one audit log entry per changed column only.
        Stores raw data in database (except passwords which are always masked).

        Args:
            model: SQLAlchemy model instance that was updated.
            old_values: Dictionary of old values before the update.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
            extra_metadata: Additional metadata to store.
        """
        try:
            table_name = model.__tablename__
            
            # Skip excluded tables
            if self._should_skip_table(table_name):
                return

            # Get record ID
            record_id = self._get_record_id(model)
            if not record_id:
                logger.warning(
                    f"Cannot audit UPDATE for {table_name}: no record ID found"
                )
                return

            # Extract current columns
            new_columns = self._extract_columns(model)
            
            # Create audit entries only for changed columns
            audit_entries = []
            occurred_at = datetime.now(timezone.utc)
            
            for column_name, new_value in new_columns.items():
                old_value = old_values.get(column_name)
                
                # Convert old_value to string (old_values comes from external dict 
                # and may contain raw Python types like bool, datetime, etc.)
                if old_value is not None:
                    if isinstance(old_value, datetime):
                        old_value = old_value.isoformat()
                    else:
                        old_value = str(old_value)
                
                # Only create audit entry if value changed
                if old_value != new_value:
                    # Only mask sensitive fields (security requirement), store everything else as-is
                    masked_old = self.mask_sensitive_only(column_name, old_value)
                    masked_new = self.mask_sensitive_only(column_name, new_value)

                    audit_entry = AuditLogModel(
                        account_id=account_id,
                        operation="UPDATE",
                        table_name=table_name,
                        record_id=record_id,
                        column_name=column_name,
                        old_value=masked_old,
                        new_value=masked_new,
                        user_id=user_id,
                        user_email=user_email,
                        user_name=user_name,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_id=request_id,
                        occurred_at=occurred_at,
                        extra_metadata=extra_metadata,
                    )
                    audit_entries.append(audit_entry)
            
            # Batch create audit entries
            if audit_entries:
                await self.repository.create_batch(audit_entries)
                logger.debug(
                    f"Captured {len(audit_entries)} audit entries for UPDATE {table_name}",
                    record_id=record_id,
                )
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(
                f"Failed to capture audit log for UPDATE {model.__tablename__}",
                error=str(e),
                exc_info=True,
            )

    async def capture_delete(
        self,
        model: Any,
        user_id: str,
        user_email: str,
        user_name: str,
        account_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Capture audit log entries for a DELETE operation.

        Creates one audit log entry per column with new_value=NULL.
        Stores raw data in database (except passwords which are always masked).

        Args:
            model: SQLAlchemy model instance that was deleted.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
            extra_metadata: Additional metadata to store.
        """

        try:
            table_name = model.__tablename__
            
            # Skip excluded tables
            if self._should_skip_table(table_name):
                return

            # Get record ID
            record_id = self._get_record_id(model)
            if not record_id:
                logger.warning(
                    f"Cannot audit DELETE for {table_name}: no record ID found"
                )
                return

            # Extract all columns and their values
            columns = self._extract_columns(model)
            
            # Create audit entries
            audit_entries = []
            occurred_at = datetime.now(timezone.utc)
            
            for column_name, old_value in columns.items():
                # Only mask sensitive fields (security requirement), store everything else as-is
                masked_value = self.mask_sensitive_only(column_name, old_value)

                audit_entry = AuditLogModel(
                    account_id=account_id,
                    operation="DELETE",
                    table_name=table_name,
                    record_id=record_id,
                    column_name=column_name,
                    old_value=masked_value,
                    new_value=None,  # NULL for DELETE
                    user_id=user_id,
                    user_email=user_email,
                    user_name=user_name,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    extra_metadata=extra_metadata,
                )
                audit_entries.append(audit_entry)
            
            # Batch create audit entries
            if audit_entries:
                await self.repository.create_batch(audit_entries)
                logger.debug(
                    f"Captured {len(audit_entries)} audit entries for DELETE {table_name}",
                    record_id=record_id,
                )
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(
                f"Failed to capture audit log for DELETE {model.__tablename__}",
                error=str(e),
                exc_info=True,
            )

    def _should_skip_table(self, table_name: str) -> bool:
        """Check if a table should be excluded from auditing.

        Args:
            table_name: Name of the table.

        Returns:
            True if the table should be skipped, False otherwise.
        """
        return table_name in self.EXCLUDED_TABLES

    def _get_record_id(self, model: Any) -> Optional[str]:
        """Extract the record ID from a SQLAlchemy model or snapshot.

        Args:
            model: SQLAlchemy model instance or snapshot.

        Returns:
            Record ID as a string, or None if not found.
        """
        # Handle snapshot
        if hasattr(model, "__is_snapshot__"):
             pk_name = model.primary_key_name
             pk_value = getattr(model, pk_name, None)
             return str(pk_value) if pk_value is not None else None

        # Try to get the primary key from real model
        mapper = inspect(model.__class__)
        pk_columns = [col.name for col in mapper.primary_key]
        
        if not pk_columns:
            return None
        
        # Use the first primary key column
        pk_name = pk_columns[0]
        pk_value = getattr(model, pk_name, None)
        
        return str(pk_value) if pk_value is not None else None

    def _extract_columns(self, model: Any) -> dict[str, Any]:
        """Extract column names and values from a SQLAlchemy model or snapshot.

        This method extracts values directly from the instance's internal
        state dictionary to avoid lazy loading issues.

        Args:
            model: SQLAlchemy model instance or snapshot.

        Returns:
            Dictionary mapping column names to their values.
        """
        # Handle snapshot
        if hasattr(model, "__is_snapshot__"):
            columns = {}
            for col_name, value in model.__dict__.items():
                if col_name.startswith("__") or col_name == "primary_key_name":
                    continue
                
                if value is not None:
                    if isinstance(value, datetime):
                        columns[col_name] = value.isoformat()
                    else:
                        columns[col_name] = str(value)
                else:
                    columns[col_name] = None
            return columns

        mapper = inspect(model.__class__)
        columns = {}
        
        # Get the instance state to access dict directly without triggering lazy loads
        instance_state = inspect(model)
        instance_dict = instance_state.dict
        
        for column in mapper.columns:
            column_name = column.name
            # Access from instance dict directly to avoid lazy loading
            value = instance_dict.get(column_name)
            
            # Convert value to string for storage
            if value is not None:
                if isinstance(value, datetime):
                    # Store datetime as ISO format
                    columns[column_name] = value.isoformat()
                else:
                    columns[column_name] = str(value)
            else:
                columns[column_name] = None
        
        return columns

    def mask_sensitive_only(
        self, column_name: str, value: Optional[str]
    ) -> Optional[str]:
        """Mask only sensitive fields (passwords, tokens, secrets) when writing to database.

        These fields are always masked for security. All other PII is stored
        as-is in the database and masked only when retrieving for display.

        Args:
            column_name: Name of the column.
            value: Value to potentially mask.

        Returns:
            Masked value if sensitive field, original value otherwise.
        """
        if value is None:
            return None

        # Always mask sensitive fields (security requirement)
        if column_name.lower() in self.SENSITIVE_FIELDS:
            return "***"

        return value

    def mask_for_display(
        self, logs: list[AuditLogModel], user_groups: list[str], account_id: str | None = None
    ) -> list[dict]:
        """Mask PII in audit logs for display based on user permissions.

        This method returns dictionaries with masked values, avoiding
        in-place modification of ORM objects which triggers SQLAlchemy
        to persist changes.

        Args:
            logs: List of audit log models from database.
            user_groups: List of group names the user belongs to.
            account_id: Optional account ID for superadmin bypass detection.

        Returns:
            List of dictionaries with PII values masked if user lacks pii_access.
        """
        # Check if user has PII access
        should_mask = PIIMaskingService.should_mask_for_user(user_groups, account_id)

        result = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "account_id": log.account_id,
                "operation": log.operation,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "column_name": log.column_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "user_name": log.user_name,
                "es_username": log.es_username,
                "es_reason": log.es_reason,
                "es_timestamp": log.es_timestamp,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "request_id": log.request_id,
                "occurred_at": log.occurred_at,
                "checksum": log.checksum,
                "previous_hash": log.previous_hash,
                "extra_metadata": log.extra_metadata,
            }

            if should_mask:
                # Mask old_value if it's PII
                if log_dict["old_value"]:
                    log_dict["old_value"] = self._mask_pii_value(
                        log.column_name, log_dict["old_value"]
                    )

                # Mask new_value if it's PII
                if log_dict["new_value"]:
                    log_dict["new_value"] = self._mask_pii_value(
                        log.column_name, log_dict["new_value"]
                    )

            result.append(log_dict)

        return result

    def _mask_pii_value(self, column_name: str, value: str) -> str:
        """Mask PII value based on column name patterns.

        Args:
            column_name: Name of the column.
            value: Value to mask.

        Returns:
            Masked value if PII column, original value otherwise.
        """
        column_lower = column_name.lower()

        if "email" in column_lower:
            return PIIMaskingService.mask_email(value)
        elif "ssn" in column_lower or "social_security" in column_lower:
            return PIIMaskingService.mask_ssn(value)
        elif "phone" in column_lower or "mobile" in column_lower:
            return PIIMaskingService.mask_phone(value)
        elif "name" in column_lower and column_lower != "username":
            # Mask name fields but not username
            return PIIMaskingService.mask_name(value)

        return value

    async def list_logs(
        self,
        account_id: str | None = None,
        table_name: str | None = None,
        record_id: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "occurred_at",
        sort_order: str = "desc",
    ) -> tuple[list[AuditLogModel], int]:
        """List audit log entries with filters and pagination.

        Args:
            account_id: Filter by account.
            table_name: Filter by table.
            record_id: Filter by record.
            user_id: Filter by user.
            operation: Filter by operation (CREATE, UPDATE, DELETE).
            from_date: Filter from this timestamp.
            to_date: Filter to this timestamp.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            sort_by: Field to sort by.
            sort_order: Sort order (asc or desc).

        Returns:
            Tuple of (list of logs, total count).
        """
        return await self.repository.list_logs(
            account_id=account_id,
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            operation=operation,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_log_by_id(self, log_id: int) -> Optional[AuditLogModel]:
        """Get a single audit log entry by ID.

        Args:
            log_id: ID of the audit log entry.

        Returns:
            The audit log entry, or None if not found.
        """
        return await self.repository.get_by_id(log_id)

    async def export_logs(
        self,
        format: str,
        user_groups: list[str],
        account_id_for_filter: str | None = None,
        account_id_for_pii: str | None = None,
        table_name: str | None = None,
        record_id: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[bytes, str]:
        """Export audit logs in the specified format.

        Args:
            format: Export format (csv, json).
            user_groups: List of group names for PII masking.
            account_id_for_filter: Filter by account.
            account_id_for_pii: Account ID for PII masking superadmin bypass.
            table_name: Filter by table.
            record_id: Filter by record.
            user_id: Filter by user.
            operation: Filter by operation.
            from_date: Start date.
            to_date: End date.

        Returns:
            Tuple of (content as bytes, media type).
        """
        # Fetch all matching logs (no pagination for export)
        logs, _ = await self.repository.list_logs(
            account_id=account_id_for_filter,
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            operation=operation,
            from_date=from_date,
            to_date=to_date,
            limit=10000,  # Cap at 10k for safety
        )

        # Mask PII based on user's group membership (returns dicts)
        logs = self.mask_for_display(logs, user_groups, account_id_for_pii)

        if format.lower() == "json":
            data = [
                {
                    "id": log["id"],
                    "occurred_at": log["occurred_at"].isoformat(),
                    "operation": log["operation"],
                    "table_name": log["table_name"],
                    "record_id": log["record_id"],
                    "column_name": log["column_name"],
                    "old_value": log["old_value"],
                    "new_value": log["new_value"],
                    "user_email": log["user_email"],
                    "ip_address": log["ip_address"],
                    "checksum": log["checksum"],
                }
                for log in logs
            ]
            content = json.dumps(data, indent=2).encode("utf-8")
            return content, "application/json"

        elif format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "ID",
                    "Timestamp",
                    "Operation",
                    "Table",
                    "Record ID",
                    "Column",
                    "Old Value",
                    "New Value",
                    "User",
                    "IP Address",
                    "Checksum",
                ]
            )
            for log in logs:
                writer.writerow(
                    [
                        log["id"],
                        log["occurred_at"].isoformat(),
                        log["operation"],
                        log["table_name"],
                        log["record_id"],
                        log["column_name"],
                        log["old_value"],
                        log["new_value"],
                        log["user_email"],
                        log["ip_address"],
                        log["checksum"],
                    ]
                )
            content = output.getvalue().encode("utf-8")
            return content, "text/csv"

        else:
            raise ValueError(f"Unsupported export format: {format}")
