"""add_timezone_support_to_all_tables

Revision ID: 60d278c6a3e3
Revises: f793cd9fde21
Create Date: 2026-01-24 21:56:01.175896

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60d278c6a3e3"
down_revision: str | Sequence[str] | None = "f793cd9fde21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add timezone support to all tables."""
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        # Table: accounts
        op.execute("ALTER TABLE accounts ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE accounts ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: audit_log
        op.execute("ALTER TABLE audit_log ALTER COLUMN es_timestamp TYPE TIMESTAMP WITH TIME ZONE USING es_timestamp AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE audit_log ALTER COLUMN occurred_at TYPE TIMESTAMP WITH TIME ZONE USING occurred_at AT TIME ZONE 'UTC';")

        # Table: email_templates
        op.execute("ALTER TABLE email_templates ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE email_templates ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: macros
        op.execute("ALTER TABLE macros ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE macros ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: invitations
        op.execute("ALTER TABLE invitations ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE invitations ALTER COLUMN accepted_at TYPE TIMESTAMP WITH TIME ZONE USING accepted_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE invitations ALTER COLUMN email_sent_at TYPE TIMESTAMP WITH TIME ZONE USING email_sent_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE invitations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")

        # Table: email_logs
        op.execute("ALTER TABLE email_logs ALTER COLUMN sent_at TYPE TIMESTAMP WITH TIME ZONE USING sent_at AT TIME ZONE 'UTC';")

        # Table: groups
        op.execute("ALTER TABLE groups ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE groups ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: collections
        op.execute("ALTER TABLE collections ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE collections ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: collection_rules
        op.execute("ALTER TABLE collection_rules ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE collection_rules ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: configurations
        op.execute("ALTER TABLE configurations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE configurations ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';")

        # Table: oauth_states
        op.execute("ALTER TABLE oauth_states ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC';")
        op.execute("ALTER TABLE oauth_states ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';")


def downgrade() -> None:
    """Downgrade schema - revert to naive timestamps."""
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        # Rever to TIMESTAMP WITHOUT TIME ZONE (naive)
        for table, columns in {
            "accounts": ["created_at", "updated_at"],
            "audit_log": ["es_timestamp", "occurred_at"],
            "email_templates": ["created_at", "updated_at"],
            "macros": ["created_at", "updated_at"],
            "invitations": ["expires_at", "accepted_at", "email_sent_at", "created_at"],
            "email_logs": ["sent_at"],
            "groups": ["created_at", "updated_at"],
            "collections": ["created_at", "updated_at"],
            "collection_rules": ["created_at", "updated_at"],
            "configurations": ["created_at", "updated_at"],
            "oauth_states": ["expires_at", "created_at"],
        }.items():
            for col in columns:
                op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP WITHOUT TIME ZONE USING {col}::text::timestamp;")
