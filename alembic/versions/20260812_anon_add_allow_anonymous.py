"""add_allow_anonymous_to_collection_rules

Revision ID: 20260812_anon
Revises: 20260812_files
Create Date: 2026-08-12 00:00:00.000000

Anonymous reachability becomes an explicit per-collection opt-in (VAPT M-08).
An empty rule means "no restriction for my users"; it must not also mean
"reachable by anyone on the internet, in whichever tenant the X-Account-ID
header names". Existing collections default to false — closed — so a
deployment that relied on an empty rule for public access has to say so.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_anon"
down_revision: str | Sequence[str] | None = "20260812_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("collection_rules", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "allow_anonymous",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment="Whether unauthenticated callers may reach this collection",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("collection_rules", schema=None) as batch_op:
        batch_op.drop_column("allow_anonymous")
