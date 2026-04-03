"""create_endpoints_tables

Revision ID: 20260403_endpoints
Revises: 20260403_hook_executions
Create Date: 2026-04-03 00:00:00.000000

Creates the ``endpoints`` and ``endpoint_executions`` tables for
F8.2: Custom Endpoints (Serverless Functions).

- endpoints: stores custom HTTP endpoint definitions per account
- endpoint_executions: per-invocation log (status, duration, request snapshot, response)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260403_endpoints"
down_revision: str | Sequence[str] | None = "20260403_hook_executions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create endpoints and endpoint_executions tables."""
    op.create_table(
        "endpoints",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
            comment="Endpoint ID (UUID)",
        ),
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
            comment="Human-readable name for this endpoint",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional description",
        ),
        sa.Column(
            "path",
            sa.String(length=500),
            nullable=False,
            comment="URL path template starting with /; supports :param segments",
        ),
        sa.Column(
            "method",
            sa.String(length=10),
            nullable=False,
            comment="HTTP method: GET, POST, PUT, PATCH, DELETE",
        ),
        sa.Column(
            "auth_required",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether a valid auth token is required",
        ),
        sa.Column(
            "condition",
            sa.Text(),
            nullable=True,
            comment="Optional rule expression; request denied (403) if evaluates False",
        ),
        sa.Column(
            "actions",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="[]",
            comment="Ordered list of action configs to execute",
        ),
        sa.Column(
            "response_template",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment='Response template: {"status": 200, "body": {...}, "headers": {...}}',
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether this endpoint is active",
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
            comment="User ID of the creator",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id", "path", "method",
            name="uq_endpoints_account_path_method",
        ),
    )
    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        batch_op.create_index("ix_endpoints_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_endpoints_enabled", ["enabled"], unique=False)

    # Create endpoint_executions table
    op.create_table(
        "endpoint_executions",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
            comment="Execution ID (UUID)",
        ),
        sa.Column(
            "endpoint_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to endpoints table",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            comment="Execution outcome: success, failed, or partial",
        ),
        sa.Column(
            "http_status",
            sa.Integer(),
            nullable=False,
            server_default="200",
            comment="HTTP status code returned to the caller",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Wall-clock execution time in milliseconds",
        ),
        sa.Column(
            "request_data",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Snapshot of the incoming request (body, query params, path params)",
        ),
        sa.Column(
            "response_body",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Actual response body sent to the caller",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error details if execution failed",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When this execution occurred (UTC)",
        ),
        sa.ForeignKeyConstraint(
            ["endpoint_id"],
            ["endpoints.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("endpoint_executions", schema=None) as batch_op:
        batch_op.create_index(
            "ix_endpoint_executions_endpoint_id", ["endpoint_id"], unique=False
        )
        batch_op.create_index(
            "ix_endpoint_executions_endpoint_executed",
            ["endpoint_id", "executed_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema: drop endpoint_executions and endpoints tables."""
    with op.batch_alter_table("endpoint_executions", schema=None) as batch_op:
        batch_op.drop_index("ix_endpoint_executions_endpoint_executed")
        batch_op.drop_index("ix_endpoint_executions_endpoint_id")

    op.drop_table("endpoint_executions")

    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        batch_op.drop_index("ix_endpoints_enabled")
        batch_op.drop_index("ix_endpoints_account_id")

    op.drop_table("endpoints")
