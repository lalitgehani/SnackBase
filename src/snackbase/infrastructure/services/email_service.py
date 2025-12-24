"""Email service for sending emails.

Provides email sending functionality for invitations and notifications.
For development, emails are logged to the console. In production, integrate
with an email service provider (e.g., SendGrid, AWS SES, Mailgun).
"""

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize the email service.

        Args:
            base_url: Base URL for the application (used in email links).
        """
        self.base_url = base_url

    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        account_name: str,
        token: str,
    ) -> None:
        """Send an invitation email.

        Args:
            to_email: Recipient email address.
            inviter_name: Name of the user who sent the invitation.
            account_name: Name of the account the user is invited to.
            token: Invitation token for accepting the invitation.
        """
        accept_url = f"{self.base_url}/api/v1/invitations/{token}/accept"

        subject = f"You've been invited to join {account_name} on SnackBase"
        body = f"""
Hello,

{inviter_name} has invited you to join {account_name} on SnackBase.

To accept this invitation and create your account, use the following token:

Token: {token}

Or visit this URL to accept:
{accept_url}

This invitation will expire in 48 hours.

If you did not expect this invitation, you can safely ignore this email.

Best regards,
The SnackBase Team
        """.strip()

        # For development: log the email to console
        logger.info(
            f"[EMAIL] Sending invitation email\n"
            f"To: {to_email}\n"
            f"Subject: {subject}\n"
            f"Body:\n{body}\n"
            f"{'=' * 80}"
        )

        # TODO: In production, integrate with an email service provider
        # Example with SendGrid:
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        #
        # message = Mail(
        #     from_email='noreply@snackbase.com',
        #     to_emails=to_email,
        #     subject=subject,
        #     plain_text_content=body
        # )
        # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # await sg.send(message)


# Default email service instance
email_service = EmailService()
