"""add_hook_condition_and_executions

Revision ID: 20260403_hook_executions
Revises: 20260402_hooks
Create Date: 2026-04-03 00:00:00.000000

Adds the ``condition`` column to the ``hooks`` table and creates the
``hook_executions`` table for F8.1: API-Defined Hooks.

- hooks.condition: optional rule expression evaluated at execution time
- hook_executions: per-execution log (status, actions run, errors, duration)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260403_hook_executions"
down_revision: str | Sequence[str] | None = "20260402_hooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add condition to hooks, create hook_executions."""
    # Add condition column to existing hooks table
    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "condition",
                sa.Text(),
                nullable=True,
                comment="Optional rule expression; hook fires only if condition evaluates to True",
            )
        )

    # Create hook_executions table
    op.create_table(
        "hook_executions",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
            comment="Execution ID (UUID)",
        ),
        sa.Column(
            "hook_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to hooks table",
        ),
        sa.Column(
            "trigger_type",
            sa.String(length=50),
            nullable=False,
            comment="How this execution was triggered: event, schedule, or manual",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            comment="Execution outcome: success, failed, or partial",
        ),
        sa.Column(
            "actions_executed",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of actions that were attempted",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error details if execution failed",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Wall-clock execution time in milliseconds",
        ),
        sa.Column(
            "execution_context",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Snapshot of the event context (record, collection, etc.)",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When this execution occurred (UTC)",
        ),
        sa.ForeignKeyConstraint(
            ["hook_id"],
            ["hooks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("hook_executions", schema=None) as batch_op:
        batch_op.create_index("ix_hook_executions_hook_id", ["hook_id"], unique=False)
        batch_op.create_index(
            "ix_hook_executions_hook_executed",
            ["hook_id", "executed_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema: drop hook_executions, remove condition from hooks."""
    with op.batch_alter_table("hook_executions", schema=None) as batch_op:
        batch_op.drop_index("ix_hook_executions_hook_executed")
        batch_op.drop_index("ix_hook_executions_hook_id")

    op.drop_table("hook_executions")

    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.drop_column("condition")
