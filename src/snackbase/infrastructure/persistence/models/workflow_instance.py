"""SQLAlchemy model for workflow run instances (F8.3).

Each time a workflow is triggered a new WorkflowInstanceModel is created.
It tracks the current execution state, the accumulated context (trigger data
+ per-step outputs), and links to the resume job when paused on a wait step.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class WorkflowInstanceModel(Base):
    """SQLAlchemy model for the workflow_instances table.

    Attributes:
        id: Primary key (UUID string).
        workflow_id: FK to workflows (CASCADE delete).
        account_id: Tenant scoping.
        status: pending | running | waiting | completed | failed | cancelled.
        current_step: Name of the step currently executing (or last executed).
        context: Accumulated execution context:
            {"trigger": {...}, "steps": {"step_name": {"output": {...}}}}
        started_at: When the instance began executing.
        completed_at: When the instance reached a terminal state.
        error_message: Error detail if status is failed.
        resume_job_id: Job ID of the scheduled resume job (wait_delay steps).
    """

    __tablename__ = "workflow_instances"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Instance ID (UUID)",
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent workflow ID",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Tenant account ID (denormalised for fast scoping queries)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        comment="Execution status: pending | running | waiting | completed | failed | cancelled",
    )
    current_step: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Name of the step currently executing or last executed",
    )
    context: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Accumulated context: trigger data + per-step outputs",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the instance started executing",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the instance reached a terminal state",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail when status is failed",
    )
    resume_job_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="Job ID of the scheduled resume job for wait_delay steps",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowInstance(id={self.id}, workflow_id={self.workflow_id}, "
            f"status={self.status}, current_step={self.current_step!r})>"
        )
