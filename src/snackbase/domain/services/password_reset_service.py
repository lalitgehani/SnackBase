"""Service for password reset logic.

Handles token generation, sending reset emails, and resetting passwords.
"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.core.logging import get_logger
from snackbase.domain.entities.password_reset import PasswordResetToken
from snackbase.infrastructure.auth.password_hasher import hash_password
from snackbase.infrastructure.persistence.models.user import UserModel
from snackbase.infrastructure.persistence.repositories.password_reset_repository import (
    PasswordResetRepository,
)
from snackbase.infrastructure.persistence.repositories.user_repository import UserRepository
from snackbase.infrastructure.persistence.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from snackbase.infrastructure.services.email_service import EmailService

logger = get_logger(__name__)


class PasswordResetService:
    """Service for handling password reset business logic."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        reset_repo: PasswordResetRepository,
        refresh_token_repo: RefreshTokenRepository,
        email_service: EmailService,
    ) -> None:
        """Initialize the password reset service.

        Args:
            session: SQLAlchemy async session.
            user_repo: Repository for user operations.
            reset_repo: Repository for password reset token operations.
            refresh_token_repo: Repository for refresh token operations.
            email_service: Service for sending emails.
        """
        self.session = session
        self.user_repo = user_repo
        self.reset_repo = reset_repo
        self.refresh_token_repo = refresh_token_repo
        self.email_service = email_service

    async def send_reset_email(
        self, user_id: str, email: str, account_id: str
    ) -> bool:
        """Generate a password reset token and send the reset email.

        Args:
            user_id: ID of the user requesting password reset.
            email: Email address to send reset link to.
            account_id: Account ID for context and email provider selection.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        # Generate token entity and plain token (1 hour expiration)
        entity, raw_token = PasswordResetToken.generate(user_id, email, expires_in_seconds=3600)

        # Store token in database (this automatically invalidates old tokens)
        await self.reset_repo.create(entity)

        # Get app_url for reset link
        system_vars = await self.email_service._get_system_variables(self.session, account_id)
        app_url = system_vars.get("app_url", "")
        
        # Build reset URL
        # Format: {app_url}/reset-password?token={token}
        reset_url = f"{app_url.rstrip('/')}/reset-password?token={raw_token}"

        logger.info(
            "Sending password reset email",
            user_id=user_id,
            email=email,
            account_id=account_id,
        )

        # Send email using template
        success = await self.email_service.send_template_email(
            session=self.session,
            to=email,
            template_type="password_reset",
            variables={
                "reset_url": reset_url,
                "token": raw_token,
                "email": email,
            },
            account_id=account_id,
        )

        if success:
            await self.session.commit()
            logger.info("Password reset email sent successfully", user_id=user_id, email=email)
        else:
            await self.session.rollback()
            logger.error("Failed to send password reset email", user_id=user_id, email=email)

        return success

    async def reset_password(self, token_plain: str, new_password: str) -> UserModel | None:
        """Reset a user's password using a valid token.

        Args:
            token_plain: The raw token string sent to the user.
            new_password: The new password to set.

        Returns:
            The user model if reset succeeded, None if token is invalid or expired.
        """
        # Look up token by its hash
        token = await self.reset_repo.get_by_token(token_plain)

        if not token or not token.is_valid():
            logger.info("Password reset failed: token invalid or expired")
            return None

        # Get user
        user = await self.user_repo.get_by_id(token.user_id)
        if not user:
            logger.error("Password reset failed: user not found", user_id=token.user_id)
            return None

        # Update password
        user.password_hash = hash_password(new_password)
        await self.user_repo.update(user)

        # Mark token as used
        await self.reset_repo.mark_as_used(token.id)

        # Invalidate all refresh tokens for this user (force re-login on all devices)
        revoked_count = await self.refresh_token_repo.revoke_all_for_user(
            user.id, user.account_id
        )

        # Commit changes
        await self.session.commit()

        logger.info(
            "Password reset successfully",
            user_id=user.id,
            email=user.email,
            account_id=user.account_id,
            refresh_tokens_revoked=revoked_count,
        )
        return user

    async def verify_reset_token(self, token_plain: str) -> tuple[bool, datetime | None]:
        """Verify if a password reset token is valid without using it.

        Args:
            token_plain: The raw token string to verify.

        Returns:
            A tuple of (is_valid, expires_at). If invalid, expires_at is None.
        """
        # Look up token by its hash
        token = await self.reset_repo.get_by_token(token_plain)

        if not token:
            logger.info("Token verification failed: token not found")
            return False, None

        is_valid = token.is_valid()
        expires_at = token.expires_at if is_valid else None

        logger.info(
            "Token verification completed",
            is_valid=is_valid,
            expires_at=expires_at,
        )
        return is_valid, expires_at
