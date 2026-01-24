"""SQLAlchemy model for the email_logs table.

Email logs provide an audit trail of all email sending attempts.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class EmailLogModel(Base):
    """SQLAlchemy model for the email_logs table.

    Logs track all email sending attempts for audit and debugging.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        template_type: Template type used (e.g., 'email_verification').
        recipient_email: Email address of the recipient.
        provider: Email provider used (e.g., 'smtp', 'ses', 'resend').
        status: Delivery status ('sent', 'failed', 'pending').
        error_message: Error message if status is 'failed' (nullable).
        variables: Template variables used for rendering (nullable).
        sent_at: Timestamp when the email was sent or attempted.
    """

    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Email log ID (UUID)",
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
        comment="Template type used (e.g., 'email_verification')",
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email address of the recipient",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Email provider used (e.g., 'smtp', 'ses', 'resend')",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Delivery status ('sent', 'failed', 'pending')",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if status is 'failed'",
    )
    variables: Mapped[dict[str, str] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Template variables used for rendering",
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the email was sent or attempted",
    )

    # Relationships
    account: Mapped["AccountModel"] = relationship(  # noqa: F821
        "AccountModel",
        back_populates="email_logs",
    )

    __table_args__ = (
        # Check constraint for valid status values
        CheckConstraint(
            "status IN ('sent', 'failed', 'pending')",
            name="ck_email_logs_status",
        ),
        # Index for efficient lookups by status
        Index("ix_email_logs_status", "status"),
        # Index for efficient lookups by account and status
        Index("ix_email_logs_account_status", "account_id", "status"),
        # Index for efficient lookups by sent_at for time-based queries
        Index("ix_email_logs_sent_at", "sent_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmailLog(id={self.id}, recipient={self.recipient_email}, "
            f"status={self.status}, sent_at={self.sent_at})>"
        )
