"""Email service for sending emails.

Provides email sending functionality with template support, provider abstraction,
and comprehensive logging for audit purposes.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.models.email_log import EmailLogModel
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
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
        config_repository: ConfigurationRepository,
    ) -> None:
        """Initialize the email service.

        Args:
            template_repository: Repository for email templates.
            log_repository: Repository for email logs.
            config_repository: Repository for configuration settings.
        """
        self.template_repository = template_repository
        self.log_repository = log_repository
        self.config_repository = config_repository
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
                sent_at=datetime.now(UTC),
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
                sent_at=datetime.now(UTC),
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

    async def _get_system_variables(
        self,
        session: AsyncSession,
        account_id: str,
    ) -> dict[str, str]:
        """Fetch system configuration variables.

        Args:
            session: Database session.
            account_id: Account ID for configuration lookup.

        Returns:
            Dictionary of system variables (app_name, app_url, support_email).
        """
        # Try to get account-specific system config, fallback to system-level
        system_config = await self.config_repository.get_config(
            category="system_settings",
            account_id=account_id,
            provider_name="system",
            is_system=False,
        )

        # Fallback to system-level config if no account-specific config
        if system_config is None:
            # Use the SYSTEM_ACCOUNT_ID constant (00000000-0000-0000-0000-000000000000)
            SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
            system_config = await self.config_repository.get_config(
                category="system_settings",
                account_id=SYSTEM_ACCOUNT_ID,
                provider_name="system",
                is_system=True,
            )

        # Return default values if no config found
        if system_config is None or system_config.config is None:
            return {
                "app_name": "SnackBase",
                "app_url": "",
                "support_email": "",
            }

        # Extract values from config
        config_data = system_config.config
        return {
            "app_name": config_data.get("app_name", "SnackBase"),
            "app_url": config_data.get("app_url", ""),
            "support_email": config_data.get("support_email", ""),
        }

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

        # Merge system variables with user-provided variables
        system_vars = await self._get_system_variables(session, account_id)
        merged_variables = {**system_vars, **variables}  # User variables override system

        # Render template
        try:
            subject = self.renderer.render(template.subject, merged_variables)
            html_body = self.renderer.render(template.html_body, merged_variables)
            text_body = self.renderer.render(template.text_body, merged_variables)
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
