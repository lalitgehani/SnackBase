"""AWS SES email provider implementation.

Uses boto3 for email sending via Amazon Simple Email Service (SES).
"""

import asyncio
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict

from snackbase.core.logging import get_logger
from snackbase.infrastructure.services.email.email_provider import EmailProvider

logger = get_logger(__name__)


class AWSESSettings(BaseModel):
    """Configuration settings for the AWS SES provider."""

    model_config = ConfigDict(from_attributes=True)

    region: str = "us-east-1"
    access_key_id: str
    secret_access_key: str
    from_email: str
    from_name: str = "SnackBase"
    reply_to: Optional[str] = None
    timeout: int = 10


class AWSESProvider(EmailProvider):
    """AWS SES email provider implementation.

    Sends emails using Amazon Simple Email Service via boto3.
    """

    def __init__(self, settings: AWSESSettings) -> None:
        """Initialize the AWS SES provider.

        Args:
            settings: AWS SES configuration settings.
        """
        self.settings = settings
        self._client = None

    def _get_client(self):
        """Get or create the SES client.

        Returns:
            boto3 SES client instance.
        """
        if self._client is None:
            self._client = boto3.client(
                "ses",
                region_name=self.settings.region,
                aws_access_key_id=self.settings.access_key_id,
                aws_secret_access_key=self.settings.secret_access_key,
            )
        return self._client

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
        """Send an email via AWS SES.

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
            Exception: If SES sending fails.
        """
        source = f"{from_name or self.settings.from_name} <{from_email or self.settings.from_email}>"
        
        reply_addresses = []
        reply_addr = reply_to or self.settings.reply_to
        if reply_addr:
            reply_addresses.append(reply_addr)

        message = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        }

        try:
            # boto3 is synchronous, so we run it in a thread pool
            def _send():
                client = self._get_client()
                return client.send_email(
                    Source=source,
                    Destination={"ToAddresses": [to]},
                    Message=message,
                    ReplyToAddresses=reply_addresses,
                )

            response = await asyncio.to_thread(_send)
            
            logger.info(
                "Email sent via AWS SES",
                message_id=response.get("MessageId"),
                to=to,
                region=self.settings.region,
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            # Handle SES-specific errors
            if error_code == "MessageRejected":
                logger.error(
                    "AWS SES rejected the message",
                    error=error_message,
                    to=to,
                )
            elif error_code == "AccountSendingPausedException":
                logger.error(
                    "AWS SES account sending is paused",
                    error=error_message,
                )
            elif error_code == "MailFromDomainNotVerifiedException":
                logger.error(
                    "AWS SES from domain not verified",
                    error=error_message,
                    from_email=from_email or self.settings.from_email,
                )
            else:
                logger.error(
                    "AWS SES client error",
                    error_code=error_code,
                    error=error_message,
                    to=to,
                )
            raise

        except BotoCoreError as e:
            logger.error("AWS SES boto core error", error=str(e), to=to)
            raise

        except Exception as e:
            logger.error("Failed to send email via AWS SES", error=str(e), to=to)
            raise

    async def test_connection(self) -> tuple[bool, str | None]:
        """Test the AWS SES connection and credentials.

        Uses GetSendQuota API to verify credentials and return quota information.

        Returns:
            Tuple of (success: bool, error_message: str | None).
        """
        try:
            # boto3 is synchronous, so we run it in a thread pool
            def _test():
                client = self._get_client()
                return client.get_send_quota()

            response = await asyncio.to_thread(_test)
            
            # Extract quota information
            max_24_hour_send = response.get("Max24HourSend", 0)
            sent_last_24_hours = response.get("SentLast24Hours", 0)
            max_send_rate = response.get("MaxSendRate", 0)
            
            success_msg = (
                f"AWS SES connection successful. "
                f"Quota: {sent_last_24_hours:.0f}/{max_24_hour_send:.0f} emails sent in last 24h, "
                f"max send rate: {max_send_rate:.0f} emails/second"
            )
            
            logger.info(
                "AWS SES connection test successful",
                region=self.settings.region,
                max_24_hour_send=max_24_hour_send,
                sent_last_24_hours=sent_last_24_hours,
                max_send_rate=max_send_rate,
            )
            
            return True, success_msg

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            error_msg = f"AWS SES connection failed ({error_code}): {error_message}"
            logger.error(
                "AWS SES connection test failed",
                error_code=error_code,
                error=error_message,
                region=self.settings.region,
            )
            return False, error_msg

        except BotoCoreError as e:
            error_msg = f"AWS SES boto core error: {str(e)}"
            logger.error("AWS SES boto core error", error=str(e))
            return False, error_msg

        except Exception as e:
            error_msg = f"AWS SES connection test failed: {str(e)}"
            logger.error("AWS SES connection test failed", error=str(e))
            return False, error_msg
