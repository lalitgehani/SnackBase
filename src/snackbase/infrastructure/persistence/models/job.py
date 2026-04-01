"""SQLAlchemy model for the background job queue.

Provides a persistent, database-backed job queue with status tracking,
retry logic, and priority ordering.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class JobModel(Base):
    """SQLAlchemy model for the jobs table.

    Represents a unit of work to be executed asynchronously by the job worker.
    Jobs are persisted to the database, enabling reliable delivery, retry on
    failure, and observability.

    Attributes:
        id: Primary key (UUID string).
        queue: Named queue for grouping related jobs (default: "default").
        handler: Registered string identifier mapping to a Python callable.
        payload: JSON payload passed to the handler.
        status: Current job status (pending, running, completed, failed, retrying, dead).
        priority: Execution priority; lower integer = higher priority (default: 0).
        run_at: Earliest datetime the job may be picked up (None = immediately).
        started_at: When the worker began executing this job.
        completed_at: When the job completed successfully.
        failed_at: When the job last failed.
        error_message: Most recent error/exception message.
        attempt_number: Number of attempts made so far (starts at 0).
        max_retries: Maximum number of retry attempts before marking dead.
        retry_delay_seconds: Base delay in seconds; exponential backoff applied.
        created_at: When the job was enqueued.
        created_by: User ID who enqueued the job (nullable for system jobs).
        account_id: Account scoping (nullable for cross-account system jobs).
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Job ID (UUID)",
    )
    queue: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
        server_default="default",
        index=True,
        comment="Named queue for grouping related jobs",
    )
    handler: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Registered handler identifier (maps to a Python callable)",
    )
    payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        comment="JSON payload passed to the handler function",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        comment="Job status: pending, running, completed, failed, retrying, dead",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
        comment="Execution priority (lower integer = higher priority)",
    )
    run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Earliest datetime to execute this job (None = immediately)",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the worker began executing this job",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job completed successfully",
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job last failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Most recent error or exception message (truncated to 5000 chars)",
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of attempts made so far (0 = not yet attempted)",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        comment="Maximum retry attempts before marking the job dead",
    )
    retry_delay_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        server_default="60",
        comment="Base retry delay in seconds; exponential backoff: delay * 2^attempt",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the job was enqueued",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID who enqueued the job (null for system jobs)",
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Account ID for tenant scoping (null for cross-account system jobs)",
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, handler={self.handler}, status={self.status}, queue={self.queue})>"
