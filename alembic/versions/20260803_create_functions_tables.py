"""create_functions_tables

Revision ID: 20260803_functions
Revises: 20260803_wh_secrets
Create Date: 2026-08-03 00:00:00.000000

Creates tables for SnackBase Functions (tenant-deployed Python FaaS):
- functions
- function_versions
- function_executions
- function_secrets
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision: str = "20260803_functions"
down_revision: str | Sequence[str] | None = "20260803_wh_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create functions-related tables."""
    op.create_table(
        "functions",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Function ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column("slug", sa.String(length=64), nullable=False, comment="URL slug unique per account"),
        sa.Column("name", sa.String(length=200), nullable=False, comment="Human-readable name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional description"),
        sa.Column(
            "entrypoint",
            sa.String(length=255),
            nullable=False,
            server_default="handler.py",
            comment="Entrypoint source file relative path",
        ),
        sa.Column(
            "auth_required",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether a valid auth token is required to invoke",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether the function accepts invokes",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ACTIVE",
            comment="Lifecycle status: ACTIVE, REMOVED, THROTTLED",
        ),
        sa.Column(
            "active_version_id",
            sa.String(length=36),
            nullable=True,
            comment="Currently active function_versions.id",
        ),
        sa.Column(
            "grants",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
            comment="Admin-client capability grants (deny-by-default)",
        ),
        sa.Column("created_by", sa.String(length=36), nullable=True, comment="User ID of the creator"),
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
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "slug", name="uq_functions_account_slug"),
    )
    with op.batch_alter_table("functions", schema=None) as batch_op:
        batch_op.create_index("ix_functions_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_functions_enabled", ["enabled"], unique=False)
        batch_op.create_index(
            "ix_functions_account_enabled",
            ["account_id", "enabled"],
            unique=False,
        )

    op.create_table(
        "function_versions",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Version ID (UUID)"),
        sa.Column(
            "function_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to functions table",
        ),
        sa.Column("version", sa.Integer(), nullable=False, comment="Monotonic version number"),
        sa.Column(
            "source_files",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
            comment="Map of relative path -> source content",
        ),
        sa.Column(
            "dependencies",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="[]",
            comment="Exact pin list (pkg==ver)",
        ),
        sa.Column("sha256", sa.String(length=64), nullable=False, comment="Content hash"),
        sa.Column("env_path", sa.Text(), nullable=True, comment="Filesystem path to the version venv"),
        sa.Column("created_by", sa.String(length=36), nullable=True, comment="Deployer user ID"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Deploy timestamp (UTC)",
        ),
        sa.ForeignKeyConstraint(["function_id"], ["functions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("function_versions", schema=None) as batch_op:
        batch_op.create_index("ix_function_versions_function_id", ["function_id"], unique=False)

    op.create_table(
        "function_executions",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Execution ID (UUID)"),
        sa.Column(
            "function_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to functions table",
        ),
        sa.Column(
            "version_id",
            sa.String(length=36),
            nullable=True,
            comment="Version that was executed",
        ),
        sa.Column("status", sa.String(length=20), nullable=False, comment="success|failed|timeout"),
        sa.Column(
            "http_status",
            sa.Integer(),
            nullable=False,
            server_default="200",
            comment="HTTP status returned to the caller",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="Duration in ms"),
        sa.Column(
            "request_data",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Redacted request snapshot",
        ),
        sa.Column(
            "response_body",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Response body (truncated/redacted)",
        ),
        sa.Column("stdout", sa.Text(), nullable=True, comment="Captured stdout"),
        sa.Column("stderr", sa.Text(), nullable=True, comment="Captured stderr"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error details"),
        sa.Column(
            "used_admin_client",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Whether get_admin_client() was used",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When this execution occurred (UTC)",
        ),
        sa.ForeignKeyConstraint(["function_id"], ["functions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["function_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("function_executions", schema=None) as batch_op:
        batch_op.create_index("ix_function_executions_function_id", ["function_id"], unique=False)
        batch_op.create_index("ix_function_executions_executed_at", ["executed_at"], unique=False)
        batch_op.create_index(
            "ix_function_executions_function_executed",
            ["function_id", "executed_at"],
            unique=False,
        )

    op.create_table(
        "function_secrets",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Secret ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column("name", sa.String(length=256), nullable=False, comment="Env var name"),
        sa.Column("value_encrypted", sa.Text(), nullable=False, comment="Fernet-encrypted value"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Last update timestamp (UTC)",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "name", name="uq_function_secrets_account_name"),
    )
    with op.batch_alter_table("function_secrets", schema=None) as batch_op:
        batch_op.create_index("ix_function_secrets_account_id", ["account_id"], unique=False)


def downgrade() -> None:
    """Drop functions tables (children first)."""
    with op.batch_alter_table("function_secrets", schema=None) as batch_op:
        batch_op.drop_index("ix_function_secrets_account_id")
    op.drop_table("function_secrets")

    with op.batch_alter_table("function_executions", schema=None) as batch_op:
        batch_op.drop_index("ix_function_executions_function_executed")
        batch_op.drop_index("ix_function_executions_executed_at")
        batch_op.drop_index("ix_function_executions_function_id")
    op.drop_table("function_executions")

    with op.batch_alter_table("function_versions", schema=None) as batch_op:
        batch_op.drop_index("ix_function_versions_function_id")
    op.drop_table("function_versions")

    with op.batch_alter_table("functions", schema=None) as batch_op:
        batch_op.drop_index("ix_functions_account_enabled")
        batch_op.drop_index("ix_functions_enabled")
        batch_op.drop_index("ix_functions_account_id")
    op.drop_table("functions")
