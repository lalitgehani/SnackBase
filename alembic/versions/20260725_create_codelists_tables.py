"""create_codelists_tables

Revision ID: 20260725_codelists
Revises: 20260403_workflows
Create Date: 2026-07-25

Creates first-class codelist tables:
- codelists
- codelist_values
- codelist_value_labels
- codelist_account_overrides

Creates empty codelist tables (no platform-default dictionary seed).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "20260725_codelists"
down_revision: str | Sequence[str] | None = "20260403_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    """Create empty codelist tables (operators create dictionaries as needed)."""
    op.create_table(
        "codelists",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Codelist ID (UUID)"),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
            comment="Stable codelist identifier (e.g. regions)",
        ),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Display name"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "definition", sa.Text(), nullable=True, comment="Formal definition / notes"
        ),
        sa.Column("scope", sa.String(length=20), nullable=False, comment="system | account"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Always populated; system account UUID for system lists",
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="True for system-scope lists",
        ),
        sa.Column(
            "is_extensible",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Account may add extension values when true",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Builtin lists cannot be hard-deleted",
        ),
        sa.Column(
            "external_code",
            sa.String(length=100),
            nullable=True,
            comment="External terminology code (e.g. CDISC)",
        ),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column(
            "metadata",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "code", name="uq_codelists_account_code"),
    )
    with op.batch_alter_table("codelists", schema=None) as batch_op:
        batch_op.create_index("ix_codelists_code", ["code"], unique=False)
        batch_op.create_index("ix_codelists_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_codelists_is_system", ["is_system"], unique=False)
        batch_op.create_index("ix_codelists_scope", ["scope"], unique=False)

    op.create_table(
        "codelist_values",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("codelist_id", sa.String(length=36), nullable=False),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
            comment="Stable submission value",
        ),
        sa.Column("external_code", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "scope",
            sa.String(length=20),
            nullable=False,
            comment="system | account (extension)",
        ),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="System account for system values; tenant for extensions",
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["codelist_id"], ["codelists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "codelist_id",
            "code",
            "account_id",
            name="uq_codelist_values_list_code_account",
        ),
    )
    with op.batch_alter_table("codelist_values", schema=None) as batch_op:
        batch_op.create_index("ix_codelist_values_codelist_id", ["codelist_id"], unique=False)
        batch_op.create_index("ix_codelist_values_account_id", ["account_id"], unique=False)
        batch_op.create_index("ix_codelist_values_code", ["code"], unique=False)
        batch_op.create_index("ix_codelist_values_is_active", ["is_active"], unique=False)

    op.create_table(
        "codelist_value_labels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("value_id", sa.String(length=36), nullable=False),
        sa.Column(
            "language",
            sa.String(length=20),
            nullable=False,
            comment="BCP-47 language tag (en, ja)",
        ),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["value_id"], ["codelist_values.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "value_id",
            "language",
            name="uq_codelist_value_labels_value_language",
        ),
    )
    with op.batch_alter_table("codelist_value_labels", schema=None) as batch_op:
        batch_op.create_index(
            "ix_codelist_value_labels_value_id", ["value_id"], unique=False
        )
        batch_op.create_index(
            "ix_codelist_value_labels_language", ["language"], unique=False
        )

    op.create_table(
        "codelist_account_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("codelist_id", sa.String(length=36), nullable=False),
        sa.Column("value_id", sa.String(length=36), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="visible",
            comment="visible | hidden",
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column(
            "metadata_override",
            JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["codelist_id"], ["codelists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["value_id"], ["codelist_values.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "value_id",
            name="uq_codelist_overrides_account_value",
        ),
    )
    with op.batch_alter_table("codelist_account_overrides", schema=None) as batch_op:
        batch_op.create_index(
            "ix_codelist_overrides_account_id", ["account_id"], unique=False
        )
        batch_op.create_index(
            "ix_codelist_overrides_codelist_id", ["codelist_id"], unique=False
        )
        batch_op.create_index(
            "ix_codelist_overrides_value_id", ["value_id"], unique=False
        )
        batch_op.create_index(
            "ix_codelist_overrides_account_value",
            ["account_id", "value_id"],
            unique=False,
        )

    # Ensure system account exists (idempotent) — required for system-scoped codelists later
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            f"""
            INSERT INTO accounts (id, account_code, slug, name, created_at, updated_at)
            VALUES (
                '{SYSTEM_ACCOUNT_ID}',
                'SY0000',
                'system',
                'System Account',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO NOTHING
            """
        )
    else:
        op.execute(
            f"""
            INSERT OR IGNORE INTO accounts (id, account_code, slug, name, created_at, updated_at)
            VALUES (
                '{SYSTEM_ACCOUNT_ID}',
                'SY0000',
                'system',
                'System Account',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        )


def downgrade() -> None:
    """Drop codelist tables."""
    with op.batch_alter_table("codelist_account_overrides", schema=None) as batch_op:
        batch_op.drop_index("ix_codelist_overrides_account_value")
        batch_op.drop_index("ix_codelist_overrides_value_id")
        batch_op.drop_index("ix_codelist_overrides_codelist_id")
        batch_op.drop_index("ix_codelist_overrides_account_id")
    op.drop_table("codelist_account_overrides")

    with op.batch_alter_table("codelist_value_labels", schema=None) as batch_op:
        batch_op.drop_index("ix_codelist_value_labels_language")
        batch_op.drop_index("ix_codelist_value_labels_value_id")
    op.drop_table("codelist_value_labels")

    with op.batch_alter_table("codelist_values", schema=None) as batch_op:
        batch_op.drop_index("ix_codelist_values_is_active")
        batch_op.drop_index("ix_codelist_values_code")
        batch_op.drop_index("ix_codelist_values_account_id")
        batch_op.drop_index("ix_codelist_values_codelist_id")
    op.drop_table("codelist_values")

    with op.batch_alter_table("codelists", schema=None) as batch_op:
        batch_op.drop_index("ix_codelists_scope")
        batch_op.drop_index("ix_codelists_is_system")
        batch_op.drop_index("ix_codelists_account_id")
        batch_op.drop_index("ix_codelists_code")
    op.drop_table("codelists")
