"""create_hooks_table

Revision ID: 20260402_hooks
Revises: 20260401_jobs
Create Date: 2026-04-02 00:00:00.000000

Creates the ``hooks`` table, which is the shared schema for both
scheduled tasks (F7.3) and API-defined event-triggered hooks (F8.1).

A hook's ``trigger`` JSON field determines when it fires:
  - Schedule: {"type": "schedule", "cron": "0 9 * * MON"}
  - Event:    {"type": "event", "event": "records.create", ...}  (F8.1)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260402_hooks"
down_revision: str | Sequence[str] | None = "20260401_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create hooks table."""
    op.create_table(
        "hooks",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Hook ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
            comment="Human-readable name for this hook",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional description",
        ),
        sa.Column(
            "trigger",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            comment='Trigger definition: {"type": "schedule", "cron": "..."} or {"type": "event", ...}',
        ),
        sa.Column(
            "actions",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="[]",
            comment="List of actions to execute when the hook fires",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether this hook is active",
        ),
        sa.Column(
            "last_run_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this hook last fired (UTC)",
        ),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Next scheduled fire time (UTC); only meaningful for schedule-type hooks",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Last update timestamp (UTC)",
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            nullable=True,
            comment="User ID of the creator (nullable for system hooks)",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.create_index("ix_hooks_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_hooks_enabled", ["enabled"], unique=False)
        batch_op.create_index("ix_hooks_next_run_at", ["next_run_at"], unique=False)
        # Composite index for the scheduler's hot path: get_due_scheduled_hooks query
        batch_op.create_index(
            "ix_hooks_scheduler_poll",
            ["enabled", "next_run_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema: drop hooks table."""
    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.drop_index("ix_hooks_scheduler_poll")
        batch_op.drop_index("ix_hooks_next_run_at")
        batch_op.drop_index("ix_hooks_enabled")
        batch_op.drop_index("ix_hooks_account_id")

    op.drop_table("hooks")
