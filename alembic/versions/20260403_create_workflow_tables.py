"""create_workflow_tables

Revision ID: 20260403_workflows
Revises: 20260403_endpoints
Create Date: 2026-04-03 00:00:00.000000

Creates the ``workflows``, ``workflow_instances``, and ``workflow_step_logs``
tables for F8.3: Workflow Engine (Multi-Step Automation).

- workflows: stores workflow definitions (trigger config + step graph)
- workflow_instances: per-run execution state with accumulated context
- workflow_step_logs: per-step audit trail within an instance
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260403_workflows"
down_revision: str | Sequence[str] | None = "20260403_endpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create workflows, workflow_instances, and workflow_step_logs tables."""

    # ------------------------------------------------------------------ #
    # workflows
    # ------------------------------------------------------------------ #
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(36), nullable=False, comment="Workflow ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(36),
            nullable=False,
            comment="Tenant account ID (FK to accounts)",
        ),
        sa.Column("name", sa.String(200), nullable=False, comment="Human-readable workflow name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional description"),
        sa.Column(
            "trigger_type",
            sa.String(20),
            nullable=False,
            comment="Trigger type: event | schedule | manual | webhook",
        ),
        sa.Column(
            "trigger_config",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
            comment="Trigger configuration JSON",
        ),
        sa.Column(
            "steps",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="[]",
            comment="Ordered list of step definition dicts",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether this workflow accepts new triggers",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Last update timestamp",
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            nullable=True,
            comment="User ID who created this workflow",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.create_index("ix_workflows_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_workflows_trigger_type", ["trigger_type"], unique=False)

    # ------------------------------------------------------------------ #
    # workflow_instances
    # ------------------------------------------------------------------ #
    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.String(36), nullable=False, comment="Instance ID (UUID)"),
        sa.Column(
            "workflow_id",
            sa.String(36),
            nullable=False,
            comment="Parent workflow ID (FK to workflows)",
        ),
        sa.Column("account_id", sa.String(36), nullable=False, comment="Tenant account ID"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="Execution status: pending | running | waiting | completed | failed | cancelled",
        ),
        sa.Column(
            "current_step",
            sa.String(200),
            nullable=True,
            comment="Name of the step currently executing or last executed",
        ),
        sa.Column(
            "context",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
            comment="Accumulated execution context: trigger data + per-step outputs",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When the instance started executing",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the instance reached a terminal state",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error detail when status is failed",
        ),
        sa.Column(
            "resume_job_id",
            sa.String(36),
            nullable=True,
            comment="Job ID of the scheduled resume job for wait_delay steps",
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("workflow_instances", schema=None) as batch_op:
        batch_op.create_index("ix_workflow_instances_workflow_id", ["workflow_id"], unique=False)
        batch_op.create_index("ix_workflow_instances_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_workflow_instances_status", ["status"], unique=False)

    # ------------------------------------------------------------------ #
    # workflow_step_logs
    # ------------------------------------------------------------------ #
    op.create_table(
        "workflow_step_logs",
        sa.Column("id", sa.String(36), nullable=False, comment="Step log ID (UUID)"),
        sa.Column(
            "instance_id",
            sa.String(36),
            nullable=False,
            comment="Parent workflow instance ID (FK to workflow_instances)",
        ),
        sa.Column(
            "workflow_id",
            sa.String(36),
            nullable=False,
            comment="Workflow ID (denormalised for fast queries)",
        ),
        sa.Column("account_id", sa.String(36), nullable=False, comment="Tenant account ID"),
        sa.Column("step_name", sa.String(200), nullable=False, comment="Step name as defined in the workflow"),
        sa.Column(
            "step_type",
            sa.String(50),
            nullable=False,
            comment="Step type: action | condition | wait_delay | loop | parallel | etc.",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="success",
            comment="Step result: success | failed | skipped",
        ),
        sa.Column(
            "input",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Snapshot of inputs passed to the step",
        ),
        sa.Column(
            "output",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Snapshot of the step's output data",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error detail when status is failed",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When step execution began",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When step execution finished",
        ),
        sa.ForeignKeyConstraint(["instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("workflow_step_logs", schema=None) as batch_op:
        batch_op.create_index("ix_workflow_step_logs_instance_id", ["instance_id"], unique=False)
        batch_op.create_index("ix_workflow_step_logs_workflow_id", ["workflow_id"], unique=False)
        batch_op.create_index("ix_workflow_step_logs_account_id", ["account_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop workflow tables in reverse dependency order."""
    with op.batch_alter_table("workflow_step_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_workflow_step_logs_account_id")
        batch_op.drop_index("ix_workflow_step_logs_workflow_id")
        batch_op.drop_index("ix_workflow_step_logs_instance_id")
    op.drop_table("workflow_step_logs")

    with op.batch_alter_table("workflow_instances", schema=None) as batch_op:
        batch_op.drop_index("ix_workflow_instances_status")
        batch_op.drop_index("ix_workflow_instances_account_id")
        batch_op.drop_index("ix_workflow_instances_workflow_id")
    op.drop_table("workflow_instances")

    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.drop_index("ix_workflows_trigger_type")
        batch_op.drop_index("ix_workflows_account_id")
    op.drop_table("workflows")
