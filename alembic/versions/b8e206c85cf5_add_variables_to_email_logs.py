"""add_variables_to_email_logs

Revision ID: b8e206c85cf5
Revises: 1799ee5d7311
Create Date: 2026-01-10 01:01:22.870502

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e206c85cf5"
down_revision: str | Sequence[str] | None = "1799ee5d7311"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add variables column to email_logs table
    # Use JSON type with JSONB variant for PostgreSQL
    with op.batch_alter_table("email_logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "variables",
                sa.JSON(),
                nullable=True,
                comment="Template variables used for rendering",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove variables column from email_logs table
    with op.batch_alter_table("email_logs", schema=None) as batch_op:
        batch_op.drop_column("variables")

