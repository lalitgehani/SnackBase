"""add_is_default_to_configurations

Revision ID: f4a8b2c1d9e7
Revises: 79cb467d7d03
Create Date: 2026-02-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a8b2c1d9e7"
down_revision: str | Sequence[str] | None = "79cb467d7d03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_default column to configurations table."""
    with op.batch_alter_table("configurations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_default",
                sa.Boolean(),
                nullable=False,
                server_default="0",
                comment="Whether this is the default provider for its category and account scope",
            )
        )
        batch_op.create_index(
            "ix_configurations_is_default",
            ["category", "account_id", "is_default"],
            unique=False,
        )


def downgrade() -> None:
    """Remove is_default column from configurations table."""
    with op.batch_alter_table("configurations", schema=None) as batch_op:
        batch_op.drop_index("ix_configurations_is_default")
        batch_op.drop_column("is_default")
