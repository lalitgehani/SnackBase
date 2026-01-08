"""Repository for email log persistence operations.

Provides operations for creating and querying email logs for audit purposes.
"""

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.email_log import EmailLogModel


class EmailLogRepository:
    """Repository for email log database operations.

    Handles email log creation and querying with filtering and pagination.
    """

    async def create(
        self,
        session: AsyncSession,
        log: EmailLogModel,
    ) -> EmailLogModel:
        """Create a new email log entry.

        Args:
            session: Database session.
            log: Email log to create.

        Returns:
            Created email log.
        """
        session.add(log)
        await session.flush()
        await session.refresh(log)
        return log

    async def get_by_id(
        self,
        session: AsyncSession,
        log_id: str,
    ) -> EmailLogModel | None:
        """Get email log by ID.

        Args:
            session: Database session.
            log_id: Log ID.

        Returns:
            EmailLogModel if found, None otherwise.
        """
        result = await session.execute(
            select(EmailLogModel).where(EmailLogModel.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list_logs(
        self,
        session: AsyncSession,
        account_id: str | None = None,
        status: str | None = None,
        template_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[Sequence[EmailLogModel], int]:
        """List email logs with optional filters and pagination.

        Args:
            session: Database session.
            account_id: Optional filter by account ID.
            status: Optional filter by status ('sent', 'failed', 'pending').
            template_type: Optional filter by template type.
            start_date: Optional filter by start date (inclusive).
            end_date: Optional filter by end date (inclusive).
            limit: Maximum number of results (default: 25).
            offset: Number of results to skip (default: 0).

        Returns:
            Tuple of (list of email logs, total count).
        """
        from sqlalchemy import func

        # Build query with filters
        query = select(EmailLogModel)

        if account_id is not None:
            query = query.where(EmailLogModel.account_id == account_id)
        if status is not None:
            query = query.where(EmailLogModel.status == status)
        if template_type is not None:
            query = query.where(EmailLogModel.template_type == template_type)
        if start_date is not None:
            query = query.where(EmailLogModel.sent_at >= start_date)
        if end_date is not None:
            query = query.where(EmailLogModel.sent_at <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply ordering and pagination
        query = query.order_by(EmailLogModel.sent_at.desc())
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await session.execute(query)
        logs = result.scalars().all()

        return logs, total
