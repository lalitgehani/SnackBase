"""create_webhooks_tables

Revision ID: 20260330_webhooks
Revises: f4a8b2c1d9e7
Create Date: 2026-03-30 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260330_webhooks"
down_revision: str | Sequence[str] | None = "f4a8b2c1d9e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Webhook ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column(
            "url",
            sa.String(length=2048),
            nullable=False,
            comment="Destination URL for webhook HTTP POST",
        ),
        sa.Column(
            "collection",
            sa.String(length=100),
            nullable=False,
            comment="Collection name to watch",
        ),
        sa.Column(
            "events",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            comment="JSON list of events: create, update, delete",
        ),
        sa.Column(
            "secret",
            sa.String(length=100),
            nullable=False,
            comment="HMAC-SHA256 signing secret",
        ),
        sa.Column(
            "filter",
            sa.Text(),
            nullable=True,
            comment="Optional rule expression to conditionally fire webhook",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether the webhook is active",
        ),
        sa.Column(
            "headers",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Optional custom HTTP headers",
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
            sa.String(length=36),
            nullable=True,
            comment="User ID of who created the webhook",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("webhooks", schema=None) as batch_op:
        batch_op.create_index("ix_webhooks_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_webhooks_collection", ["collection"], unique=False)
        batch_op.create_index("ix_webhooks_enabled", ["enabled"], unique=False)

    op.create_table(
        "webhook_deliveries",
        sa.Column(
            "id", sa.String(length=36), nullable=False, comment="Delivery ID (UUID)"
        ),
        sa.Column(
            "webhook_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to webhooks table",
        ),
        sa.Column(
            "event",
            sa.String(length=50),
            nullable=False,
            comment="Event type that triggered this delivery",
        ),
        sa.Column(
            "payload",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            comment="Full JSON payload sent to the webhook URL",
        ),
        sa.Column(
            "response_status",
            sa.Integer(),
            nullable=True,
            comment="HTTP response status code",
        ),
        sa.Column(
            "response_body",
            sa.String(length=5000),
            nullable=True,
            comment="Truncated response body",
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Attempt number (1 = first try)",
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the delivery succeeded",
        ),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the next retry is scheduled",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Delivery status: pending, delivered, failed, retrying",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="When this delivery record was created",
        ),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("webhook_deliveries", schema=None) as batch_op:
        batch_op.create_index(
            "ix_webhook_deliveries_webhook_id", ["webhook_id"], unique=False
        )
        batch_op.create_index(
            "ix_webhook_deliveries_status", ["status"], unique=False
        )
        batch_op.create_index(
            "ix_webhook_deliveries_next_retry_at", ["next_retry_at"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("webhook_deliveries", schema=None) as batch_op:
        batch_op.drop_index("ix_webhook_deliveries_next_retry_at")
        batch_op.drop_index("ix_webhook_deliveries_status")
        batch_op.drop_index("ix_webhook_deliveries_webhook_id")

    op.drop_table("webhook_deliveries")

    with op.batch_alter_table("webhooks", schema=None) as batch_op:
        batch_op.drop_index("ix_webhooks_enabled")
        batch_op.drop_index("ix_webhooks_collection")
        batch_op.drop_index("ix_webhooks_account_id")

    op.drop_table("webhooks")
