"""SQLAlchemy model for the email_templates table.

Email templates store customizable email content with Jinja2 variable support.
Templates can be account-specific or system-level defaults.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class EmailTemplateModel(Base):
    """SQLAlchemy model for the email_templates table.

    Templates support Jinja2 variable substitution and localization.
    System-level templates (is_builtin=true) cannot be deleted.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        template_type: Template type identifier (e.g., 'email_verification').
        locale: Language/locale code (e.g., 'en', 'es').
        subject: Email subject line (supports Jinja2 variables).
        html_body: HTML email body (supports Jinja2 variables).
        text_body: Plain text email body (supports Jinja2 variables).
        enabled: Whether this template is active.
        is_builtin: Whether this is a built-in system template.
        created_at: Timestamp when the template was created.
        updated_at: Timestamp when the template was last updated.
    """

    __tablename__ = "email_templates"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Email template ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to accounts table",
    )
    template_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Template type (e.g., 'email_verification', 'password_reset')",
    )
    locale: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="en",
        comment="Language/locale code (e.g., 'en', 'es', 'fr')",
    )
    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email subject line (supports Jinja2 variables)",
    )
    html_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="HTML email body (supports Jinja2 variables)",
    )
    text_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Plain text email body (supports Jinja2 variables)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="Whether this template is active",
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="Built-in templates cannot be deleted",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    account: Mapped["AccountModel"] = relationship(  # noqa: F821
        "AccountModel",
        back_populates="email_templates",
    )

    __table_args__ = (
        # Unique constraint: one template per (account, type, locale)
        UniqueConstraint(
            "account_id",
            "template_type",
            "locale",
            name="uq_email_templates_account_type_locale",
        ),
        # Index for efficient lookups by template type
        Index("ix_email_templates_template_type", "template_type"),
        # Index for efficient lookups by account and type
        Index("ix_email_templates_account_type", "account_id", "template_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmailTemplate(id={self.id}, type={self.template_type}, "
            f"locale={self.locale}, account_id={self.account_id})>"
        )
