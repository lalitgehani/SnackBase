"""create_token_blacklist

Revision ID: 79cb467d7d03
Revises: 60d278c6a3e3
Create Date: 2026-02-14 18:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '79cb467d7d03'
down_revision: str | Sequence[str] | None = '60d278c6a3e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('token_blacklist',
        sa.Column('id', sa.Text(), nullable=False, comment='Token ID (from payload)'),
        sa.Column('token_type', sa.Text(), nullable=False, comment='Type of token blacklisted'),
        sa.Column('revoked_at', sa.Integer(), nullable=False, comment='Unix timestamp of revocation'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Optional reason for revocation'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_token_blacklist_token_type'), ['token_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_token_blacklist_token_type'))

    op.drop_table('token_blacklist')
