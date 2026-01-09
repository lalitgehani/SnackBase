"""Resend email provider implementation.

Uses the Resend Python SDK for email sending via Resend API.
"""

import asyncio

import resend
from pydantic import BaseModel, ConfigDict

from snackbase.core.logging import get_logger
from snackbase.infrastructure.services.email.email_provider import EmailProvider

logger = get_logger(__name__)


class ResendSettings(BaseModel):
    """Configuration settings for the Resend provider."""

    model_config = ConfigDict(from_attributes=True)

    api_key: str
    from_email: str
    from_name: str = "SnackBase"
    reply_to: str | None = None


class ResendProvider(EmailProvider):
    """Resend email provider implementation.

    Sends emails using the Resend API via the Resend Python SDK.
    """

    def __init__(self, settings: ResendSettings) -> None:
        """Initialize the Resend provider.

        Args:
            settings: Resend configuration settings.
        """
        self.settings = settings
        # Set the API key for the Resend SDK
        resend.api_key = settings.api_key

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
        """Send an email via Resend.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML email body.
            text_body: Plain text email body.
            from_email: Sender email address (overrides settings if provided).
            from_name: Sender display name (overrides settings if provided).
            reply_to: Optional reply-to email address.

        Returns:
            True if email was sent successfully.

        Raises:
            Exception: If Resend sending fails.
        """
        sender = (
            f"{from_name or self.settings.from_name} <{from_email or self.settings.from_email}>"
        )

        # Prepare email parameters
        params = {
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }

        # Add reply-to if provided
        reply_addr = reply_to or self.settings.reply_to
        if reply_addr:
            params["reply_to"] = reply_addr

        try:
            # Resend SDK is synchronous, so we run it in a thread pool
            def _send():
                return resend.Emails.send(params)

            response = await asyncio.to_thread(_send)

            logger.info(
                "Email sent via Resend",
                email_id=response.get("id"),
                to=to,
            )
            return True

        except Exception as e:
            # Handle Resend-specific errors
            error_message = str(e)

            if "Invalid API key" in error_message or "Unauthorized" in error_message:
                logger.error(
                    "Resend authentication failed",
                    error=error_message,
                    to=to,
                )
            elif "rate limit" in error_message.lower():
                logger.error(
                    "Resend rate limit exceeded",
                    error=error_message,
                    to=to,
                )
            elif "not verified" in error_message.lower():
                logger.error(
                    "Resend from domain not verified",
                    error=error_message,
                    from_email=from_email or self.settings.from_email,
                )
            else:
                logger.error(
                    "Resend API error",
                    error=error_message,
                    to=to,
                )
            raise

    async def test_connection(self) -> tuple[bool, str | None]:
        """Test the Resend connection and API key.

        Uses the API key validation by attempting to retrieve API key details.

        Returns:
            Tuple of (success: bool, error_message: str | None).
        """
        try:
            # Resend SDK is synchronous, so we run it in a thread pool
            # We'll use a lightweight API call to validate the API key
            # The Resend SDK doesn't have a dedicated ping endpoint,
            # so we'll use the domains.list() call as a validation
            def _test():
                return resend.Domains.list()

            response = await asyncio.to_thread(_test)

            success_msg = (
                "Resend connection successful. API key is valid and ready to send emails."
            )

            logger.info(
                "Resend connection test successful",
                domains_count=len(response.get("data", [])) if isinstance(response, dict) else 0,
            )

            return True, success_msg

        except Exception as e:
            error_message = str(e)

            if "Invalid API key" in error_message or "Unauthorized" in error_message:
                error_msg = "Resend connection failed: Invalid API key"
            elif "rate limit" in error_message.lower():
                error_msg = "Resend connection failed: Rate limit exceeded"
            else:
                error_msg = f"Resend connection failed: {error_message}"

            logger.error(
                "Resend connection test failed",
                error=error_message,
            )
            return False, error_msg
