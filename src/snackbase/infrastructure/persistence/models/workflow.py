"""SQLAlchemy model for workflow definitions (F8.3).

Workflows are directed graphs of steps that can be triggered by events,
schedules, manual API calls, or inbound webhooks. The ``steps`` field
stores the full step graph as JSON.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class WorkflowModel(Base):
    """SQLAlchemy model for the workflows table.

    Attributes:
        id: Primary key (UUID string).
        account_id: Tenant scoping (FK to accounts, CASCADE delete).
        name: Human-readable workflow name.
        description: Optional description.
        trigger_type: One of event | schedule | manual | webhook.
        trigger_config: JSON config for the trigger type.
            - event:    {"type": "event", "event": "records.create", "collection": "orders", "condition": "..."}
            - schedule: {"type": "schedule", "cron": "0 9 * * MON"}
            - manual:   {"type": "manual"}
            - webhook:  {"type": "webhook", "token": "<32-char secret>"}
        steps: JSON list of step dicts. Each step has at minimum
            ``name`` (unique within the workflow) and ``type``.
        enabled: Whether this workflow is active.
        created_at: When the workflow was created.
        updated_at: When the workflow was last updated.
        created_by: User ID who created the workflow.
    """

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Workflow ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant account ID",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable workflow name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Trigger type: event | schedule | manual | webhook",
    )
    trigger_config: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Trigger configuration JSON",
    )
    steps: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
        comment="Ordered list of step definition dicts",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether this workflow accepts new triggers",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID who created this workflow",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name!r}, trigger_type={self.trigger_type})>"
