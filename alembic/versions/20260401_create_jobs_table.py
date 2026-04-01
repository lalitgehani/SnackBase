"""create_jobs_table

Revision ID: 20260401_jobs
Revises: 20260330_webhooks
Create Date: 2026-04-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260401_jobs"
down_revision: str | Sequence[str] | None = "20260330_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create jobs table."""
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Job ID (UUID)"),
        sa.Column(
            "queue",
            sa.String(length=100),
            nullable=False,
            server_default="default",
            comment="Named queue for grouping related jobs",
        ),
        sa.Column(
            "handler",
            sa.String(length=200),
            nullable=False,
            comment="Registered handler identifier (maps to a Python callable)",
        ),
        sa.Column(
            "payload",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            comment="JSON payload passed to the handler function",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Job status: pending, running, completed, failed, retrying, dead",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Execution priority (lower integer = higher priority)",
        ),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Earliest datetime to execute this job (None = immediately)",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the worker began executing this job",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the job completed successfully",
        ),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the job last failed",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Most recent error or exception message (truncated to 5000 chars)",
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of attempts made so far (0 = not yet attempted)",
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            nullable=False,
            server_default="3",
            comment="Maximum retry attempts before marking the job dead",
        ),
        sa.Column(
            "retry_delay_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
            comment="Base retry delay in seconds; exponential backoff: delay * 2^attempt",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When the job was enqueued",
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            nullable=True,
            comment="User ID who enqueued the job (null for system jobs)",
        ),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=True,
            comment="Account ID for tenant scoping (null for cross-account system jobs)",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.create_index("ix_jobs_status", ["status"], unique=False)
        batch_op.create_index("ix_jobs_queue", ["queue"], unique=False)
        batch_op.create_index("ix_jobs_priority", ["priority"], unique=False)
        batch_op.create_index("ix_jobs_run_at", ["run_at"], unique=False)
        batch_op.create_index("ix_jobs_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_jobs_handler", ["handler"], unique=False)
        # Composite index for the worker's hot path: pick_next_job query
        batch_op.create_index(
            "ix_jobs_worker_poll",
            ["status", "priority", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema: drop jobs table."""
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_jobs_worker_poll")
        batch_op.drop_index("ix_jobs_handler")
        batch_op.drop_index("ix_jobs_account_id")
        batch_op.drop_index("ix_jobs_run_at")
        batch_op.drop_index("ix_jobs_priority")
        batch_op.drop_index("ix_jobs_queue")
        batch_op.drop_index("ix_jobs_status")

    op.drop_table("jobs")
