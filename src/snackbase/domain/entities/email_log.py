"""Email log entity for tracking sent emails.

Email logs provide an audit trail of all email sending attempts,
including success/failure status and error messages.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class EmailLog:
    """Email log entity representing a sent email record.

    Logs track all email sending attempts for audit and debugging purposes.

    Attributes:
        id: Unique identifier (UUID string).
        account_id: Foreign key to the account this log belongs to.
        template_type: Template type used (e.g., 'email_verification', 'password_reset').
        recipient_email: Email address of the recipient.
        provider: Email provider used (e.g., 'smtp', 'ses', 'resend').
        status: Delivery status ('sent', 'failed', 'pending').
        error_message: Error message if status is 'failed' (nullable).
        sent_at: Timestamp when the email was sent or attempted.
    """

    id: str
    account_id: str
    template_type: str
    recipient_email: str
    provider: str
    status: str
    error_message: str | None = None
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate email log data after initialization."""
        if not self.id:
            raise ValueError("Email log ID is required")
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.template_type:
            raise ValueError("Template type is required")
        if not self.recipient_email:
            raise ValueError("Recipient email is required")
        if not self.provider:
            raise ValueError("Provider is required")
        if not self.status:
            raise ValueError("Status is required")

        valid_statuses = {"sent", "failed", "pending"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
