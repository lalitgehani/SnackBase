"""Email service for sending emails.

Provides email sending functionality with template support, provider abstraction,
and comprehensive logging for audit purposes.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

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
from snackbase.infrastructure.security.encryption import EncryptionService
from snackbase.infrastructure.services.email.aws_ses_provider import (
    AWSESProvider,
    AWSESSettings,
)
from snackbase.infrastructure.services.email.email_provider import EmailProvider
from snackbase.infrastructure.services.email.resend_provider import (
    ResendProvider,
    ResendSettings,
)
from snackbase.infrastructure.services.email.smtp_provider import (
    SMTPProvider,
    SMTPSettings,
)
from snackbase.infrastructure.services.email.template_renderer import get_template_renderer

logger = get_logger(__name__)

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


class ProviderCache:
    """Cache for email provider instances with TTL."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        """Initialize the provider cache.

        Args:
            ttl_seconds: Time-to-live for cached providers (default: 5 minutes).
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[
            str, tuple[tuple[EmailProvider, str, str, Optional[str]], datetime]
        ] = {}

    def get(
        self, key: str
    ) -> Optional[tuple[EmailProvider, str, str, Optional[str]]]:
        """Get a provider from cache if not expired.

        Args:
            key: Cache key (typically account_id).

        Returns:
            Cached provider tuple if found and not expired, None otherwise.
        """
        if key not in self._cache:
            return None

        provider_tuple, cached_at = self._cache[key]
        if datetime.now(UTC) - cached_at > timedelta(seconds=self.ttl_seconds):
            # Expired, remove from cache
            del self._cache[key]
            return None

        return provider_tuple

    def set(
        self, key: str, provider_tuple: tuple[EmailProvider, str, str, Optional[str]]
    ) -> None:
        """Store a provider tuple in cache.

        Args:
            key: Cache key (typically account_id).
            provider_tuple: Provider tuple to cache (provider, from_email, from_name, reply_to).
        """
        self._cache[key] = (provider_tuple, datetime.now(UTC))

    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries.

        Args:
            key: Specific cache key to invalidate. If None, clears entire cache.
        """
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]


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
        encryption_service: EncryptionService,
    ) -> None:
        """Initialize the email service.

        Args:
            template_repository: Repository for email templates.
            log_repository: Repository for email logs.
            config_repository: Repository for configuration settings.
            encryption_service: Encryption service for decrypting provider configs.
        """
        self.template_repository = template_repository
        self.log_repository = log_repository
        self.config_repository = config_repository
        self.encryption_service = encryption_service
        self.renderer = get_template_renderer()
        self._provider_cache = ProviderCache(ttl_seconds=300)  # 5-minute TTL

    def _create_provider(self, provider_name: str, config: dict) -> EmailProvider:
        """Factory method to create provider instances from configuration.

        Args:
            provider_name: Name of the provider (smtp, aws_ses, resend).
            config: Decrypted configuration dictionary.

        Returns:
            Instantiated email provider.

        Raises:
            ValueError: If provider name is not recognized.
        """
        if provider_name == "smtp":
            settings = SMTPSettings(**config)
            return SMTPProvider(settings)
        elif provider_name == "aws_ses":
            settings = AWSESSettings(**config)
            return AWSESProvider(settings)
        elif provider_name == "resend":
            settings = ResendSettings(**config)
            return ResendProvider(settings)
        else:
            raise ValueError(f"Unknown email provider: {provider_name}")

    async def _select_provider(
        self,
        session: AsyncSession,
        account_id: str,
    ) -> tuple[EmailProvider, str, str, Optional[str]]:
        """Select the appropriate email provider for the account.

        Selection logic:
        1. Check for account-specific enabled provider
        2. Fall back to system-level enabled provider
        3. Return error if no enabled provider found

        Args:
            session: Database session.
            account_id: Account ID for provider selection.

        Returns:
            Tuple of (provider, from_email, from_name, reply_to).

        Raises:
            ValueError: If no enabled email provider is configured.
        """
        # Try account-specific provider first
        account_configs = await self.config_repository.list_configs(
            category="email_providers",
            account_id=account_id,
            is_system=False,
            enabled_only=True,
        )

        # If no account-specific config, try system-level
        if not account_configs:
            logger.debug(
                "No account-specific email provider, falling back to system",
                account_id=account_id,
            )
            account_configs = await self.config_repository.list_configs(
                category="email_providers",
                account_id=SYSTEM_ACCOUNT_ID,
                is_system=True,
                enabled_only=True,
            )

        if not account_configs:
            error_msg = (
                "No enabled email provider configured. "
                "Please configure an email provider (SMTP, AWS SES, or Resend) "
                "before sending emails."
            )
            logger.error(error_msg, account_id=account_id)
            raise ValueError(error_msg)

        # Use the first enabled provider (they're ordered by priority)
        config_model = account_configs[0]
        provider_name = config_model.provider_name

        # Decrypt configuration
        decrypted_config = self.encryption_service.decrypt_dict(config_model.config)

        # Create provider instance
        provider = self._create_provider(provider_name, decrypted_config)

        # Extract email settings
        from_email = decrypted_config.get("from_email", "noreply@snackbase.io")
        from_name = decrypted_config.get("from_name", "SnackBase")
        reply_to = decrypted_config.get("reply_to")

        logger.info(
            "Email provider selected",
            provider=provider_name,
            account_id=account_id,
            is_system=config_model.is_system,
        )

        return provider, from_email, from_name, reply_to

    async def _get_specific_provider(
        self,
        session: AsyncSession,
        account_id: str,
        provider_name: str,
    ) -> tuple[EmailProvider, str, str, Optional[str]]:
        """Get a specific email provider.

        Args:
            session: Database session.
            account_id: Account ID.
            provider_name: Name of the provider to retrieve (e.g. 'aws_ses').

        Returns:
            Tuple of (provider, from_email, from_name, reply_to).

        Raises:
            ValueError: If provider is not configured or enabled.
        """
        # Check account level first
        config_model = await self.config_repository.get_config(
            category="email_providers",
            account_id=account_id,
            provider_name=provider_name,
            is_system=False,
        )

        # Fallback to system level if not found
        if not config_model:
            config_model = await self.config_repository.get_config(
                category="email_providers",
                account_id=SYSTEM_ACCOUNT_ID,
                provider_name=provider_name,
                is_system=True,
            )

        if not config_model or not config_model.enabled:
            raise ValueError(f"Provider '{provider_name}' is not configured or enabled.")

        # Decrypt configuration
        decrypted_config = self.encryption_service.decrypt_dict(config_model.config)

        # Create provider instance
        provider = self._create_provider(provider_name, decrypted_config)

        # Extract email settings
        from_email = decrypted_config.get("from_email", "noreply@snackbase.io")
        from_name = decrypted_config.get("from_name", "SnackBase")
        reply_to = decrypted_config.get("reply_to")

        return provider, from_email, from_name, reply_to

    async def _get_provider(
        self,
        session: AsyncSession,
        account_id: str,
    ) -> tuple[EmailProvider, str, str, Optional[str]]:
        """Get email provider with caching.

        Args:
            session: Database session.
            account_id: Account ID for provider selection.

        Returns:
            Tuple of (provider, from_email, from_name, reply_to).
        """
        # Check cache first
        cache_key = f"provider:{account_id}"
        cached_result = self._provider_cache.get(cache_key)

        if cached_result is not None:
            logger.debug("Using cached email provider", account_id=account_id)
            return cached_result

        # Select provider
        result = await self._select_provider(session, account_id)

        # Cache the full result tuple
        self._provider_cache.set(cache_key, result)

        return result

    def invalidate_provider_cache(self, account_id: Optional[str] = None) -> None:
        """Invalidate provider cache.

        Args:
            account_id: Specific account to invalidate. If None, clears entire cache.
        """
        if account_id is None:
            self._provider_cache.invalidate()
            logger.info("Email provider cache cleared")
        else:
            cache_key = f"provider:{account_id}"
            self._provider_cache.invalidate(cache_key)
            logger.info("Email provider cache invalidated", account_id=account_id)

    async def send_email(
        self,
        session: AsyncSession,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        account_id: str,
        template_type: str = "custom",
        variables: dict[str, str] | None = None,
        provider_name: str | None = None,
    ) -> bool:
        """Send an email using automatic provider selection.

        Args:
            session: Database session for logging.
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML email body.
            text_body: Plain text email body.
            account_id: Account ID for provider selection and logging.
            template_type: Template type for logging (default: 'custom').
            variables: Template variables used for rendering (optional, for logging).

        Returns:
            True if email was sent successfully, False otherwise.
        """
        log_id = str(uuid.uuid4())

        try:
            # Get provider (specific or automatic)
            if provider_name and provider_name != "auto":
                provider, from_email, from_name, reply_to = await self._get_specific_provider(
                    session, account_id, provider_name
                )
            else:
                provider, from_email, from_name, reply_to = await self._get_provider(
                    session, account_id
                )
            provider_name = provider.__class__.__name__.replace("Provider", "").lower()

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
                variables=variables,
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
                variables=variables,
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
        account_id: str,
        locale: str = "en",
        provider_name: str | None = None,
    ) -> bool:
        """Send an email using a template with automatic provider selection.

        Args:
            session: Database session.
            to: Recipient email address.
            template_type: Template type (e.g., 'email_verification').
            variables: Dictionary of variables for template rendering.
            account_id: Account ID for provider selection.
            locale: Language/locale code (default: 'en').

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
            account_id=account_id,
            template_type=template_type,
            variables=merged_variables,
            provider_name=provider_name,
        )
