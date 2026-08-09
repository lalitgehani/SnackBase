"""add_login_lockout_columns_to_users

Revision ID: 20260809_lockout
Revises: 20260803_functions
Create Date: 2026-08-09 00:00:00.000000

Adds the per-account brute-force lockout state (VAPT H-02). The counter has to
outlive the process and be shared by every instance, so it lives on the user row
rather than in memory next to the per-IP throttle.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_lockout"
down_revision: str | Sequence[str] | None = "20260803_functions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Consecutive failed login attempts; reset on success",
            )
        )
        batch_op.add_column(
            sa.Column(
                "locked_until",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Login is refused until this time after too many failed attempts",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
