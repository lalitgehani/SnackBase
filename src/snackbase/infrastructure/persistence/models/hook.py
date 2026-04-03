"""SQLAlchemy model for the hooks table.

Hooks are the shared schema for both scheduled tasks (F7.3) and
API-defined event-triggered hooks (F8.1).

A hook's ``trigger`` JSON column determines when it fires:
    - Schedule trigger: {"type": "schedule", "cron": "0 9 * * MON"}
    - Event trigger:    {"type": "event", "event": "records.create", ...}  (F8.1)

The ``actions`` column holds the list of actions to execute when the hook fires.
It is populated by F8.1; the scheduler (F7.3) passes it through to the job payload.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class HookModel(Base):
    """SQLAlchemy model for the hooks table.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        name: Human-readable name for this hook.
        description: Optional description.
        trigger: JSON object describing when this hook fires.
            Schedule: {"type": "schedule", "cron": "0 9 * * MON"}
            Event:    {"type": "event", "event": "records.create", ...}
        actions: JSON list of actions to execute.  [] until F8.1.
        enabled: Whether this hook is active.
        last_run_at: When this hook last fired (UTC, nullable).
        next_run_at: Next scheduled fire time (UTC, nullable).
            Only meaningful for schedule-type hooks.
        created_at: Creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).
        created_by: User ID of the creator (nullable).
    """

    __tablename__ = "hooks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Hook ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name for this hook",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description",
    )
    trigger: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        comment='Trigger definition: {"type": "schedule", "cron": "..."} or {"type": "event", ...}',
    )
    actions: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of actions to execute when the hook fires",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Whether this hook is active",
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this hook last fired (UTC)",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Next scheduled fire time (UTC); only meaningful for schedule-type hooks",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp (UTC)",
    )
    condition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional rule expression; hook fires only if condition evaluates to True",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID of the creator (nullable for system hooks)",
    )

    def __repr__(self) -> str:
        trigger_type = self.trigger.get("type", "?") if self.trigger else "?"
        return (
            f"<Hook(id={self.id}, name={self.name!r}, "
            f"trigger_type={trigger_type!r}, enabled={self.enabled})>"
        )
