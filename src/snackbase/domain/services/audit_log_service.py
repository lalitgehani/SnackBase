"""Audit log service for capturing data changes.

This service handles the automatic capture of audit log entries for all
CREATE, UPDATE, DELETE operations with column-level granularity.
"""

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
    }

    # Fields that should always be masked
    PASSWORD_FIELDS = {"password", "password_hash", "hashed_password"}

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
        user_groups: Optional[list[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Capture audit log entries for a CREATE operation.

        Creates one audit log entry per column with old_value=NULL.

        Args:
            model: SQLAlchemy model instance that was created.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            user_groups: List of group names the user belongs to.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
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
                # Mask sensitive values
                masked_value = self._mask_sensitive_value(
                    column_name, new_value, user_groups or []
                )
                
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
        user_groups: Optional[list[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Capture audit log entries for an UPDATE operation.

        Creates one audit log entry per changed column only.

        Args:
            model: SQLAlchemy model instance that was updated.
            old_values: Dictionary of old values before the update.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            user_groups: List of group names the user belongs to.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
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
                
                # Only create audit entry if value changed
                if old_value != new_value:
                    # Mask sensitive values
                    masked_old = self._mask_sensitive_value(
                        column_name, old_value, user_groups or []
                    )
                    masked_new = self._mask_sensitive_value(
                        column_name, new_value, user_groups or []
                    )
                    
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
        user_groups: Optional[list[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Capture audit log entries for a DELETE operation.

        Creates one audit log entry per column with new_value=NULL.

        Args:
            model: SQLAlchemy model instance that was deleted.
            user_id: ID of the user who performed the operation.
            user_email: Email of the user who performed the operation.
            user_name: Name of the user who performed the operation.
            account_id: Account context for the operation.
            user_groups: List of group names the user belongs to.
            ip_address: IP address of the client.
            user_agent: User agent string from the request.
            request_id: Correlation ID for the request.
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
                # Mask sensitive values
                masked_value = self._mask_sensitive_value(
                    column_name, old_value, user_groups or []
                )
                
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
        """Extract the record ID from a SQLAlchemy model.

        Args:
            model: SQLAlchemy model instance.

        Returns:
            Record ID as a string, or None if not found.
        """
        # Try to get the primary key
        mapper = inspect(model.__class__)
        pk_columns = [col.name for col in mapper.primary_key]
        
        if not pk_columns:
            return None
        
        # Use the first primary key column
        pk_name = pk_columns[0]
        pk_value = getattr(model, pk_name, None)
        
        return str(pk_value) if pk_value is not None else None

    def _extract_columns(self, model: Any) -> dict[str, Any]:
        """Extract column names and values from a SQLAlchemy model.

        This method extracts values directly from the instance's internal
        state dictionary to avoid lazy loading issues.

        Args:
            model: SQLAlchemy model instance.

        Returns:
            Dictionary mapping column names to their values.
        """
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

    def _mask_sensitive_value(
        self, column_name: str, value: Optional[str], user_groups: list[str]
    ) -> Optional[str]:
        """Mask sensitive values based on column name and user permissions.

        Args:
            column_name: Name of the column.
            value: Value to potentially mask.
            user_groups: List of group names the user belongs to.

        Returns:
            Masked value if sensitive, original value otherwise.
        """
        if value is None:
            return None
        
        # Always mask password fields
        if column_name.lower() in self.PASSWORD_FIELDS:
            return "***"
        
        # Check if user has PII access
        if PIIMaskingService.should_mask_for_user(user_groups):
            # Apply PII masking based on column name patterns
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
