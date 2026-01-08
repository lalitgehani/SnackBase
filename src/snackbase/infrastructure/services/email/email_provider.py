"""Abstract base class for email providers.

Defines the interface that all email providers must implement.
"""

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Abstract base class for email providers.

    All email providers (SMTP, SES, Resend, etc.) must implement this interface.
    """

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: str,
        from_name: str,
        reply_to: str | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML email body.
            text_body: Plain text email body.
            from_email: Sender email address.
            from_name: Sender display name.
            reply_to: Optional reply-to email address.

        Returns:
            True if email was sent successfully, False otherwise.

        Raises:
            Exception: If email sending fails with an error.
        """
        pass

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str | None]:
        """Test the email provider connection.

        Returns:
            Tuple of (success: bool, error_message: str | None).
            If successful, error_message is None.
            If failed, error_message contains the error details.
        """
        pass
