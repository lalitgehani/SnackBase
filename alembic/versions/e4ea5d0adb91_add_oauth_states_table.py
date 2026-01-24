"""add_oauth_states_table

Revision ID: e4ea5d0adb91
Revises: c69bf537b237
Create Date: 2026-01-01 21:44:46.460514

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


# revision identifiers, used by Alembic.
revision: str = 'e4ea5d0adb91'
down_revision: str | Sequence[str] | None = 'c69bf537b237'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create oauth_states table
    op.create_table(
        "oauth_states",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
            comment="OAuth state ID (UUID)",
        ),
        sa.Column(
            "provider_name",
            sa.String(length=100),
            nullable=False,
            comment="Target OAuth provider name",
        ),
        sa.Column(
            "state_token",
            sa.String(length=255),
            nullable=False,
            comment="Secure random state token",
        ),
        sa.Column(
            "redirect_uri",
            sa.String(length=500),
            nullable=False,
            comment="Redirect URI to return to after flow completion",
        ),
        sa.Column(
            "code_verifier",
            sa.String(length=255),
            nullable=True,
            comment="Optional PKCE code verifier",
        ),
        sa.Column(
            "metadata",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
            comment="Optional additional metadata for the flow",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            comment="Token expiration timestamp",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            comment="Token creation timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_token"),
    )

    # Create indexes
    with op.batch_alter_table("oauth_states", schema=None) as batch_op:
        batch_op.create_index(
            "ix_oauth_states_state_token",
            ["state_token"],
            unique=False,
        )
        batch_op.create_index(
            "ix_oauth_states_expires_at",
            ["expires_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    with op.batch_alter_table("oauth_states", schema=None) as batch_op:
        batch_op.drop_index("ix_oauth_states_expires_at")
        batch_op.drop_index("ix_oauth_states_state_token")

    # Drop table
    op.drop_table("oauth_states")

