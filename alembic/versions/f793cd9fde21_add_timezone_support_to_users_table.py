"""add_timezone_support_to_users_table

Revision ID: f793cd9fde21
Revises: 3f032f63cb42
Create Date: 2026-01-24 21:08:04.994044

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f793cd9fde21'
down_revision: str | Sequence[str] | None = '3f032f63cb42'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema with timezone support for users table."""
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        # For PostgreSQL, alter columns to TIMESTAMP WITH TIME ZONE
        # Using CASE to handle NULL values properly
        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN email_verified_at
            TYPE TIMESTAMP WITH TIME ZONE
            USING CASE
                WHEN email_verified_at IS NOT NULL
                THEN email_verified_at AT TIME ZONE 'UTC'
                ELSE NULL
            END;
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN created_at
            TYPE TIMESTAMP WITH TIME ZONE
            USING created_at AT TIME ZONE 'UTC';
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN updated_at
            TYPE TIMESTAMP WITH TIME ZONE
            USING updated_at AT TIME ZONE 'UTC';
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN last_login
            TYPE TIMESTAMP WITH TIME ZONE
            USING CASE
                WHEN last_login IS NOT NULL
                THEN last_login AT TIME ZONE 'UTC'
                ELSE NULL
            END;
            """
        )
    # For SQLite, no action needed - SQLite stores datetime as strings


def downgrade() -> None:
    """Downgrade schema - remove timezone support from users table."""
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        # Revert to TIMESTAMP WITHOUT TIME ZONE
        # Using CASE to handle NULL values properly
        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN email_verified_at
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING CASE
                WHEN email_verified_at IS NOT NULL
                THEN email_verified_at::text::timestamp
                ELSE NULL
            END;
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN created_at
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING created_at::text::timestamp;
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN updated_at
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING updated_at::text::timestamp;
            """
        )

        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN last_login
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING CASE
                WHEN last_login IS NOT NULL
                THEN last_login::text::timestamp
                ELSE NULL
            END;
            """
        )
    # For SQLite, no action needed
