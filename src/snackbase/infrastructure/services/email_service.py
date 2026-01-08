"""Email service for sending emails.

Provides email sending functionality with template support, provider abstraction,
and comprehensive logging for audit purposes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.models.email_log import EmailLogModel
from snackbase.infrastructure.persistence.models.email_template import EmailTemplateModel
from snackbase.infrastructure.persistence.repositories.email_log_repository import (
    EmailLogRepository,
)
from snackbase.infrastructure.persistence.repositories.email_template_repository import (
    EmailTemplateRepository,
)
from snackbase.infrastructure.services.email.email_provider import EmailProvider
from snackbase.infrastructure.services.email.template_renderer import get_template_renderer

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails with template support.

    Orchestrates email sending with provider abstraction, template rendering,
    and comprehensive logging.
    """

    def __init__(
        self,
        template_repository: EmailTemplateRepository,
        log_repository: EmailLogRepository,
    ) -> None:
        """Initialize the email service.

        Args:
            template_repository: Repository for email templates.
            log_repository: Repository for email logs.
        """
        self.template_repository = template_repository
        self.log_repository = log_repository
        self.renderer = get_template_renderer()

    async def send_email(
        self,
        session: AsyncSession,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        provider: EmailProvider,
        from_email: str,
        from_name: str,
        account_id: str,
        template_type: str = "custom",
        reply_to: str | None = None,
    ) -> bool:
        """Send an email using the specified provider.

        Args:
            session: Database session for logging.
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML email body.
            text_body: Plain text email body.
            provider: Email provider instance.
            from_email: Sender email address.
            from_name: Sender display name.
            account_id: Account ID for logging.
            template_type: Template type for logging (default: 'custom').
            reply_to: Optional reply-to email address.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        log_id = str(uuid.uuid4())
        provider_name = provider.__class__.__name__.replace("Provider", "").lower()

        try:
            # Send email via provider
            success = await provider.send_email(
                to=to,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                from_email=from_email,
                from_name=from_name,
                reply_to=reply_to,
            )

            # Log success
            log = EmailLogModel(
                id=log_id,
                account_id=account_id,
                template_type=template_type,
                recipient_email=to,
                provider=provider_name,
                status="sent" if success else "failed",
                error_message=None if success else "Provider returned failure",
                sent_at=datetime.now(timezone.utc),
            )
            await self.log_repository.create(session, log)
            await session.commit()

            logger.info(
                "Email sent successfully",
                recipient=to,
                template_type=template_type,
                provider=provider_name,
            )
            return success

        except Exception as e:
            # Log failure
            log = EmailLogModel(
                id=log_id,
                account_id=account_id,
                template_type=template_type,
                recipient_email=to,
                provider=provider_name,
                status="failed",
                error_message=str(e),
                sent_at=datetime.now(timezone.utc),
            )
            await self.log_repository.create(session, log)
            await session.commit()

            logger.error(
                "Email sending failed",
                recipient=to,
                template_type=template_type,
                provider=provider_name,
                error=str(e),
            )
            return False

    async def send_template_email(
        self,
        session: AsyncSession,
        to: str,
        template_type: str,
        variables: dict[str, str],
        provider: EmailProvider,
        from_email: str,
        from_name: str,
        account_id: str,
        locale: str = "en",
        reply_to: str | None = None,
    ) -> bool:
        """Send an email using a template.

        Args:
            session: Database session.
            to: Recipient email address.
            template_type: Template type (e.g., 'email_verification').
            variables: Dictionary of variables for template rendering.
            provider: Email provider instance.
            from_email: Sender email address.
            from_name: Sender display name.
            account_id: Account ID.
            locale: Language/locale code (default: 'en').
            reply_to: Optional reply-to email address.

        Returns:
            True if email was sent successfully, False otherwise.

        Raises:
            ValueError: If template not found or rendering fails.
        """
        # Get template with account fallback
        template = await self.template_repository.get_template(
            session=session,
            account_id=account_id,
            template_type=template_type,
            locale=locale,
        )

        if template is None:
            error_msg = f"Email template not found: {template_type} (locale: {locale})"
            logger.error(error_msg, account_id=account_id)
            raise ValueError(error_msg)

        # Render template
        try:
            subject = self.renderer.render(template.subject, variables)
            html_body = self.renderer.render(template.html_body, variables)
            text_body = self.renderer.render(template.text_body, variables)
        except Exception as e:
            error_msg = f"Template rendering failed: {str(e)}"
            logger.error(error_msg, template_type=template_type, error=str(e))
            raise ValueError(error_msg)

        # Send email
        return await self.send_email(
            session=session,
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            provider=provider,
            from_email=from_email,
            from_name=from_name,
            account_id=account_id,
            template_type=template_type,
            reply_to=reply_to,
        )
