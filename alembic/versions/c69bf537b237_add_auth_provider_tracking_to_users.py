"""add_auth_provider_tracking_to_users

Revision ID: c69bf537b237
Revises: b6a59f965907
Create Date: 2026-01-01 20:50:48.674047

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "c69bf537b237"
down_revision: str | Sequence[str] | None = "b6a59f965907"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add authentication provider tracking columns to users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        # Add auth_provider column with default 'password'
        batch_op.add_column(
            sa.Column(
                "auth_provider",
                sa.String(length=50),
                nullable=False,
                server_default="password",
                comment="Authentication provider type ('password', 'oauth', 'saml')",
            )
        )

        # Add auth_provider_name column (nullable)
        batch_op.add_column(
            sa.Column(
                "auth_provider_name",
                sa.String(length=100),
                nullable=True,
                comment="Specific provider name (e.g., 'google', 'github', 'microsoft')",
            )
        )

        # Add external_id column (nullable)
        batch_op.add_column(
            sa.Column(
                "external_id",
                sa.String(length=500),
                nullable=True,
                comment="External provider's user ID for identity linking",
            )
        )

        # Add external_email column (nullable)
        batch_op.add_column(
            sa.Column(
                "external_email",
                sa.String(length=255),
                nullable=True,
                comment="Email address from external provider (may differ from local email)",
            )
        )

        # Add profile_data column (nullable JSON) - dialect-agnostic
        batch_op.add_column(
            sa.Column(
                "profile_data",
                JSON().with_variant(JSONB(), "postgresql"),
                nullable=True,
                comment="Additional profile data from external provider",
            )
        )

        # Create index on auth_provider for efficient filtering
        batch_op.create_index(
            "ix_users_auth_provider",
            ["auth_provider"],
            unique=False,
        )

        # Create composite index on (auth_provider_name, external_id) for identity linking
        batch_op.create_index(
            "ix_users_auth_provider_name_external_id",
            ["auth_provider_name", "external_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove authentication provider tracking columns from users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        # Drop indexes first
        batch_op.drop_index("ix_users_auth_provider_name_external_id")
        batch_op.drop_index("ix_users_auth_provider")

        # Drop columns
        batch_op.drop_column("profile_data")
        batch_op.drop_column("external_email")
        batch_op.drop_column("external_id")
        batch_op.drop_column("auth_provider_name")
        batch_op.drop_column("auth_provider")

