"""add_audit_log_triggers

Revision ID: 8cebef609756
Revises: ea6f4f210d59
Create Date: 2025-12-31 16:23:36.142452

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8cebef609756'
down_revision: str | Sequence[str] | None = 'ea6f4f210d59'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema with dialect-specific triggers."""
    # Get the current database dialect
    dialect = op.get_context().dialect.name

    if dialect == "sqlite":
        # SQLite trigger to prevent UPDATE
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be updated');
            END;
            """
        )

        # SQLite trigger to prevent DELETE
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be deleted');
            END;
            """
        )
    elif dialect == "postgresql":
        # PostgreSQL requires a function for the trigger logic
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_log_update_func()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Audit log entries are immutable and cannot be updated';
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
        )

        # Create function for DELETE trigger
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_log_delete_func()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Audit log entries are immutable and cannot be deleted';
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
        )

        # PostgreSQL trigger to prevent UPDATE
        op.execute(
            """
            CREATE TRIGGER prevent_audit_log_update
            BEFORE UPDATE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_update_func();
            """
        )

        # PostgreSQL trigger to prevent DELETE
        op.execute(
            """
            CREATE TRIGGER prevent_audit_log_delete
            BEFORE DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_delete_func();
            """
        )


def downgrade() -> None:
    """Downgrade schema with dialect-specific trigger cleanup."""
    dialect = op.get_context().dialect.name

    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update ON audit_log")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete ON audit_log")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update ON audit_log")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete ON audit_log")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_update_func()")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_delete_func()")
