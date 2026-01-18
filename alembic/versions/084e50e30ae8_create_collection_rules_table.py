"""create_collection_rules_table

Revision ID: 084e50e30ae8
Revises: 7bccaa56da18
Create Date: 2026-01-19 00:19:12.172897

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "084e50e30ae8"
down_revision: str | Sequence[str] | None = "7bccaa56da18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create collection_rules table."""
    op.create_table(
        "collection_rules",
        sa.Column(
            "id", sa.String(length=36), nullable=False, comment="Collection rule ID (UUID)"
        ),
        sa.Column(
            "collection_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to collections table",
        ),
        # 5 operation rules (NULL = locked, "" = public, "expr" = filter)
        sa.Column(
            "list_rule",
            sa.Text(),
            nullable=True,
            comment="Filter expression for listing records",
        ),
        sa.Column(
            "view_rule",
            sa.Text(),
            nullable=True,
            comment="Filter expression for viewing single record",
        ),
        sa.Column(
            "create_rule",
            sa.Text(),
            nullable=True,
            comment="Validation expression for creating records",
        ),
        sa.Column(
            "update_rule",
            sa.Text(),
            nullable=True,
            comment="Filter/validation expression for updates",
        ),
        sa.Column(
            "delete_rule",
            sa.Text(),
            nullable=True,
            comment="Filter expression for deletions",
        ),
        # Field-level permissions per operation
        sa.Column(
            "list_fields",
            sa.Text(),
            nullable=False,
            server_default="*",
            comment="Fields visible in list operations (JSON array or '*')",
        ),
        sa.Column(
            "view_fields",
            sa.Text(),
            nullable=False,
            server_default="*",
            comment="Fields visible in view operations (JSON array or '*')",
        ),
        sa.Column(
            "create_fields",
            sa.Text(),
            nullable=False,
            server_default="*",
            comment="Fields allowed in create requests (JSON array or '*')",
        ),
        sa.Column(
            "update_fields",
            sa.Text(),
            nullable=False,
            server_default="*",
            comment="Fields allowed in update requests (JSON array or '*')",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        # Constraints
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", name="uq_collection_rules_collection_id"),
    )

    # Create index on collection_id for performance
    with op.batch_alter_table("collection_rules", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_collection_rules_collection_id"),
            ["collection_id"],
            unique=False,
        )


def downgrade() -> None:
    """Drop collection_rules table."""
    with op.batch_alter_table("collection_rules", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_collection_rules_collection_id"))

    op.drop_table("collection_rules")
