"""SQLAlchemy model for the hook_executions table.

Each row records the outcome of a single hook execution — whether triggered
by an event, a cron schedule, or a manual API call.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class HookExecutionModel(Base):
    """Execution log for a single hook run.

    Attributes:
        id: Primary key (UUID string).
        hook_id: Foreign key to hooks table (CASCADE delete).
        trigger_type: How this execution was triggered ("event", "schedule", "manual").
        status: Outcome of the execution ("success", "failed", "partial").
        actions_executed: How many actions were attempted.
        error_message: Error details when status is "failed" or "partial".
        duration_ms: Wall-clock execution time in milliseconds.
        execution_context: Snapshot of the triggering context (record data, event name, etc.).
        executed_at: When this execution occurred (UTC).
    """

    __tablename__ = "hook_executions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Execution ID (UUID)",
    )
    hook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to hooks table",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="How this execution was triggered: event, schedule, or manual",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Execution outcome: success, failed, or partial",
    )
    actions_executed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of actions that were attempted",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if execution failed",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Wall-clock execution time in milliseconds",
    )
    execution_context: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Snapshot of the event context (record, collection, etc.)",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this execution occurred (UTC)",
    )

    def __repr__(self) -> str:
        return (
            f"<HookExecution(id={self.id}, hook_id={self.hook_id}, "
            f"status={self.status!r}, trigger_type={self.trigger_type!r})>"
        )
