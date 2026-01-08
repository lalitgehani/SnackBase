"""add_email_tables

Revision ID: 1799ee5d7311
Revises: e4ea5d0adb91
Create Date: 2026-01-08 18:01:20.192797

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1799ee5d7311"
down_revision: str | Sequence[str] | None = "e4ea5d0adb91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_templates table
    op.create_table(
        "email_templates",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Email template ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column(
            "template_type",
            sa.String(length=50),
            nullable=False,
            comment="Template type (e.g., 'email_verification', 'password_reset')",
        ),
        sa.Column(
            "locale",
            sa.String(length=10),
            nullable=False,
            server_default="en",
            comment="Language/locale code (e.g., 'en', 'es', 'fr')",
        ),
        sa.Column(
            "subject",
            sa.String(length=255),
            nullable=False,
            comment="Email subject line (supports Jinja2 variables)",
        ),
        sa.Column(
            "html_body",
            sa.Text(),
            nullable=False,
            comment="HTML email body (supports Jinja2 variables)",
        ),
        sa.Column(
            "text_body",
            sa.Text(),
            nullable=False,
            comment="Plain text email body (supports Jinja2 variables)",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="Whether this template is active",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="Built-in templates cannot be deleted",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_email_templates_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_templates")),
        sa.UniqueConstraint(
            "account_id",
            "template_type",
            "locale",
            name="uq_email_templates_account_type_locale",
        ),
    )
    op.create_index(
        "ix_email_templates_account_id", "email_templates", ["account_id"], unique=False
    )
    op.create_index(
        "ix_email_templates_account_type",
        "email_templates",
        ["account_id", "template_type"],
        unique=False,
    )
    op.create_index("ix_email_templates_enabled", "email_templates", ["enabled"], unique=False)
    op.create_index(
        "ix_email_templates_template_type", "email_templates", ["template_type"], unique=False
    )

    # Create email_logs table
    op.create_table(
        "email_logs",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Email log ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Foreign key to accounts table",
        ),
        sa.Column(
            "template_type",
            sa.String(length=50),
            nullable=False,
            comment="Template type used (e.g., 'email_verification')",
        ),
        sa.Column(
            "recipient_email",
            sa.String(length=255),
            nullable=False,
            comment="Email address of the recipient",
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            comment="Email provider used (e.g., 'smtp', 'ses', 'resend')",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="Delivery status ('sent', 'failed', 'pending')",
        ),
        sa.Column(
            "error_message", sa.Text(), nullable=True, comment="Error message if status is 'failed'"
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when the email was sent or attempted",
        ),
        sa.CheckConstraint(
            "status IN ('sent', 'failed', 'pending')", name="ck_email_logs_status"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_email_logs_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_logs")),
    )
    op.create_index("ix_email_logs_account_id", "email_logs", ["account_id"], unique=False)
    op.create_index(
        "ix_email_logs_account_status", "email_logs", ["account_id", "status"], unique=False
    )
    op.create_index("ix_email_logs_sent_at", "email_logs", ["sent_at"], unique=False)
    op.create_index("ix_email_logs_status", "email_logs", ["status"], unique=False)
    op.create_index("ix_email_logs_template_type", "email_logs", ["template_type"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop email_logs table
    op.drop_index("ix_email_logs_template_type", table_name="email_logs")
    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_sent_at", table_name="email_logs")
    op.drop_index("ix_email_logs_account_status", table_name="email_logs")
    op.drop_index("ix_email_logs_account_id", table_name="email_logs")
    op.drop_table("email_logs")

    # Drop email_templates table
    op.drop_index("ix_email_templates_template_type", table_name="email_templates")
    op.drop_index("ix_email_templates_enabled", table_name="email_templates")
    op.drop_index("ix_email_templates_account_type", table_name="email_templates")
    op.drop_index("ix_email_templates_account_id", table_name="email_templates")
    op.drop_table("email_templates")
