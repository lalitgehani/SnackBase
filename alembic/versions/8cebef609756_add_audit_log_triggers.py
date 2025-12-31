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
    """Upgrade schema."""
    # Trigger to prevent UPDATE
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
        BEFORE UPDATE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be updated');
        END;
        """
    )

    # Trigger to prevent DELETE
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
        BEFORE DELETE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'Audit log entries are immutable and cannot be deleted');
        END;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update")
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete")
