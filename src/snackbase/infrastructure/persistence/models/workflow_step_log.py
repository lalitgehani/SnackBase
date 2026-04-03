"""SQLAlchemy model for per-step execution logs (F8.3).

Each step execution within a workflow instance is recorded here, providing
a full audit trail of what happened, when, and with what input/output.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class WorkflowStepLogModel(Base):
    """SQLAlchemy model for the workflow_step_logs table.

    Attributes:
        id: Primary key (UUID string).
        instance_id: FK to workflow_instances (CASCADE delete).
        workflow_id: Denormalised workflow ID for fast queries.
        account_id: Tenant scoping.
        step_name: Name of the step as defined in the workflow.
        step_type: Type of the step (action, condition, wait_delay, etc.).
        status: success | failed | skipped.
        input: JSON snapshot of inputs passed to the step.
        output: JSON snapshot of the step's output data.
        error_message: Error detail when status is failed.
        started_at: When step execution began.
        completed_at: When step execution finished.
    """

    __tablename__ = "workflow_step_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Step log ID (UUID)",
    )
    instance_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent workflow instance ID",
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Workflow ID (denormalised for fast queries)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Tenant account ID",
    )
    step_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Step name as defined in the workflow",
    )
    step_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Step type: action | condition | wait_delay | loop | parallel | etc.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="Step result: success | failed | skipped",
    )
    input: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Snapshot of inputs passed to the step",
    )
    output: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Snapshot of the step's output data",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail when status is failed",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When step execution began",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When step execution finished",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowStepLog(id={self.id}, instance_id={self.instance_id}, "
            f"step={self.step_name!r}, status={self.status})>"
        )
