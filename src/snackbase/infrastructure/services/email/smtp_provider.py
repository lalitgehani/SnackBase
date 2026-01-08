"""SMTP email provider implementation.

Uses aiosmtplib for asynchronous email sending via SMTP.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from pydantic import BaseModel, ConfigDict, Field

from snackbase.core.logging import get_logger
from snackbase.infrastructure.services.email.email_provider import EmailProvider

logger = get_logger(__name__)


class SMTPSettings(BaseModel):
    """Configuration settings for the SMTP provider."""

    model_config = ConfigDict(from_attributes=True)

    host: str
    port: int = 587
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: str
    from_name: str = "SnackBase"
    reply_to: Optional[str] = None
    timeout: int = 10


class SMTPProvider(EmailProvider):
    """SMTP email provider implementation.

    Sends emails using the SMTP protocol via aiosmtplib.
    """

    def __init__(self, settings: SMTPSettings) -> None:
        """Initialize the SMTP provider.

        Args:
            settings: SMTP configuration settings.
        """
        self.settings = settings

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: str,
        from_name: str,
        reply_to: Optional[str] = None,
    ) -> bool:
        """Send an email via SMTP.

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
            Exception: If SMTP connection or sending fails.
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{from_name or self.settings.from_name} <{from_email or self.settings.from_email}>"
        message["To"] = to
        
        reply_addr = reply_to or self.settings.reply_to
        if reply_addr:
            message["Reply-To"] = reply_addr

        # Add text and HTML parts
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            async with aiosmtplib.SMTP(
                hostname=self.settings.host,
                port=self.settings.port,
                use_tls=self.settings.use_ssl,  # aiosmtplib uses use_tls for SSL/TLS on connection
                timeout=self.settings.timeout,
            ) as smtp:
                if self.settings.use_tls and not self.settings.use_ssl:
                    await smtp.starttls()
                
                await smtp.login(self.settings.username, self.settings.password)
                await smtp.send_message(message)
                
            return True
        except Exception as e:
            logger.error("Failed to send email via SMTP", host=self.settings.host, error=str(e))
            raise

    async def test_connection(self) -> tuple[bool, str | None]:
        """Test the SMTP connection and authentication.

        Returns:
            Tuple of (success: bool, error_message: str | None).
        """
        try:
            async with aiosmtplib.SMTP(
                hostname=self.settings.host,
                port=self.settings.port,
                use_tls=self.settings.use_ssl,
                timeout=self.settings.timeout,
            ) as smtp:
                if self.settings.use_tls and not self.settings.use_ssl:
                    await smtp.starttls()
                
                await smtp.login(self.settings.username, self.settings.password)
                
            return True, None
        except Exception as e:
            error_msg = f"SMTP connection failed: {str(e)}"
            logger.error(error_msg, host=self.settings.host)
            return False, error_msg
