"""add view collection support

Revision ID: 20260411_view_cols
Revises: 20260403_workflows
Create Date: 2026-04-11 00:00:00.000000

Adds ``type`` and ``view_query`` columns to the ``collections`` table
to support view collections (SQL-based read-only collections).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260411_view_cols"
down_revision: str | Sequence[str] | None = "20260403_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("collections", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "type",
                sa.String(length=16),
                nullable=False,
                server_default="base",
                comment="Collection type: 'base' for physical tables, 'view' for SQL views",
            )
        )
        batch_op.add_column(
            sa.Column(
                "view_query",
                sa.Text(),
                nullable=True,
                comment="SQL query defining the view (NULL for base collections)",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("collections", schema=None) as batch_op:
        batch_op.drop_column("view_query")
        batch_op.drop_column("type")
