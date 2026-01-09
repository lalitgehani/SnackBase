"""Service for email verification logic.

Handles token generation, sending verification emails, and validating tokens.
"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.core.logging import get_logger
from snackbase.domain.entities.email_verification import EmailVerificationToken
from snackbase.infrastructure.persistence.repositories.email_verification_repository import (
    EmailVerificationRepository,
)
from snackbase.infrastructure.persistence.repositories.user_repository import UserRepository
from snackbase.infrastructure.services.email_service import EmailService

logger = get_logger(__name__)


class EmailVerificationService:
    """Service for handling email verification business logic."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        verification_repo: EmailVerificationRepository,
        email_service: EmailService,
    ) -> None:
        """Initialize the verification service.

        Args:
            session: SQLAlchemy async session.
            user_repo: Repository for user operations.
            verification_repo: Repository for verification token operations.
            email_service: Service for sending emails.
        """
        self.session = session
        self.user_repo = user_repo
        self.verification_repo = verification_repo
        self.email_service = email_service

    async def send_verification_email(
        self, user_id: str, email: str, account_id: str
    ) -> bool:
        """Generate a verification token and send the verification email.

        Args:
            user_id: ID of the user to verify.
            email: Email address to verify.
            account_id: Account ID for context and email provider selection.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        # Generate token entity and plain token
        entity, raw_token = EmailVerificationToken.generate(user_id, email)

        # Store token in database
        await self.verification_repo.create(entity)

        # Get app_url for verification link
        # We fetch system variables from the email service since it already knows how to do it
        system_vars = await self.email_service._get_system_variables(self.session, account_id)
        app_url = system_vars.get("app_url", "")
        
        # Build verification URL
        # Format: {app_url}/verify-email?token={token}
        verification_url = f"{app_url.rstrip('/')}/verify-email?token={raw_token}"

        logger.info(
            "Sending verification email",
            user_id=user_id,
            email=email,
            account_id=account_id,
        )

        # Send email using template
        success = await self.email_service.send_template_email(
            session=self.session,
            to=email,
            template_type="email_verification",
            variables={
                "verification_url": verification_url,
                "token": raw_token,
                "email": email,
            },
            account_id=account_id,
        )

        if success:
            await self.session.commit()
            logger.info("Verification email sent successfully", user_id=user_id, email=email)
        else:
            await self.session.rollback()
            logger.error("Failed to send verification email", user_id=user_id, email=email)

        return success

    async def verify_email(self, token_plain: str) -> bool:
        """Verify a user's email using a plain text token.

        Args:
            token_plain: The raw token string sent to the user.

        Returns:
            True if verification succeeded, False if token is invalid or expired.
        """
        # Look up token by its hash
        token = await self.verification_repo.get_by_token(token_plain)

        if not token or not token.is_valid():
            logger.info("Email verification failed: token invalid or expired")
            return False

        # Get user to verify
        user = await self.user_repo.get_by_id(token.user_id)
        if not user:
            logger.error("Email verification failed: user not found", user_id=token.user_id)
            return False

        # Mark user as verified
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await self.user_repo.update(user)

        # Mark token as used
        await self.verification_repo.mark_as_used(token.id)

        # Commit changes
        await self.session.commit()

        logger.info(
            "Email verified successfully",
            user_id=user.id,
            email=user.email,
            account_id=user.account_id,
        )
        return True
