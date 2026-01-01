"""add_configurations_table

Revision ID: b6a59f965907
Revises: 8cebef609756
Create Date: 2026-01-01 19:54:53.627739

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "b6a59f965907"
down_revision: str | Sequence[str] | None = "8cebef609756"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create configurations table
    op.create_table(
        "configurations",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
            comment="Configuration ID (UUID)",
        ),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table (always populated)",
        ),
        sa.Column(
            "category",
            sa.String(length=50),
            nullable=False,
            comment="Configuration category (e.g., 'auth_providers', 'email_providers')",
        ),
        sa.Column(
            "provider_name",
            sa.String(length=100),
            nullable=False,
            comment="Provider identifier (e.g., 'google', 'ses', 's3')",
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=False,
            comment="Human-readable provider name",
        ),
        sa.Column(
            "logo_url",
            sa.String(length=500),
            nullable=True,
            comment="Path to provider logo",
        ),
        sa.Column(
            "config_schema",
            sqlite.JSON(),
            nullable=True,
            comment="JSON Schema for configuration validation",
        ),
        sa.Column(
            "config",
            sqlite.JSON(),
            nullable=False,
            comment="Provider configuration as encrypted JSON",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether this configuration is active",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Built-in providers cannot be deleted",
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="True for system-level configs (SY0000), false for account-level",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Display order priority (lower = higher priority)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category",
            "provider_name",
            "account_id",
            name="uq_configurations_category_provider_account",
        ),
    )

    # Create indexes
    with op.batch_alter_table("configurations", schema=None) as batch_op:
        batch_op.create_index(
            "ix_configurations_category_account",
            ["category", "account_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_configurations_category_provider",
            ["category", "provider_name"],
            unique=False,
        )
        batch_op.create_index(
            "ix_configurations_is_system",
            ["is_system"],
            unique=False,
        )

    # Ensure system account (SY0000) exists
    # This is idempotent - if it already exists, this will be a no-op
    op.execute(
        """
        INSERT OR IGNORE INTO accounts (id, account_code, slug, name, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000000',
            'SY0000',
            'system',
            'System Account',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    with op.batch_alter_table("configurations", schema=None) as batch_op:
        batch_op.drop_index("ix_configurations_is_system")
        batch_op.drop_index("ix_configurations_category_provider")
        batch_op.drop_index("ix_configurations_category_account")

    # Drop table
    op.drop_table("configurations")

    # Note: We do NOT delete the system account on downgrade
    # as it may be in use by other parts of the system

