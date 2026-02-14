"""Unified authentication for all SnackBase token types.

Implements the Authenticator class which handles:
- Standard JWT Bearer tokens
- SnackBase tokens (sb_ak, sb_pt, sb_ot)
- Legacy API keys (sb_sk)
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth.api_key_service import api_key_service
from snackbase.infrastructure.auth.jwt_service import (
    InvalidTokenError,
    TokenExpiredError,
    jwt_service,
)
from snackbase.infrastructure.auth.token_codec import AuthenticationError, TokenCodec
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenPayload, TokenType
from snackbase.infrastructure.persistence.models import APIKeyModel, UserModel

logger = get_logger(__name__)

# System account ID for superadmins (matches dependencies.py)
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


class Authenticator:
    """Unified authentication for all token types."""

    def __init__(self, secret: Optional[str] = None):
        """Initialize the authenticator.

        Args:
            secret: Secret key for SnackBase tokens. If not provided,
                    uses the one from settings via TokenCodec.
        """
        self.secret = secret

    async def authenticate(
        self, request_headers: Dict[str, str], session: Optional[AsyncSession] = None
    ) -> AuthenticatedUser:
        """Authenticate from request headers.

        Priority:
        1. Authorization: Bearer <token>
        2. X-API-Key: <token>

        Args:
            request_headers: Dictionary of request headers.
            session: Optional database session for revocation check or legacy keys.

        Returns:
            AuthenticatedUser: The validated user context.

        Raises:
            AuthenticationError: If authentication fails.
        """
        # 1. Try Authorization header
        auth_header = request_headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            return await self._authenticate_bearer(token, session)

        # 2. Try X-API-Key header
        api_key_header = request_headers.get("X-API-Key") or request_headers.get("x-api-key")
        if api_key_header:
            logger.debug("Found X-API-Key header", key_prefix=api_key_header[:10])
            return await self._authenticate_api_key_header(api_key_header, session)

        logger.debug("No valid authentication headers found", headers=list(request_headers.keys()))
        raise AuthenticationError("Missing authentication credentials")

    async def _authenticate_bearer(
        self, token: str, session: Optional[AsyncSession]
    ) -> AuthenticatedUser:
        """Authenticate a Bearer token (either JWT or SB token)."""
        # SnackBase tokens start with 'sb_'
        if token.startswith("sb_"):
            return await self._authenticate_sb_token(token, session)
        
        # Otherwise, assume it's a standard JWT
        return await self._authenticate_jwt(token, session)

    async def _authenticate_api_key_header(
        self, token: str, session: Optional[AsyncSession]
    ) -> AuthenticatedUser:
        """Authenticate from X-API-Key header (either SB API Key or Legacy Key)."""
        # SnackBase API keys start with 'sb_ak.'
        if token.startswith("sb_ak."):
            return await self._authenticate_sb_token(token, session)
        
        # Legacy API keys start with 'sb_sk_'
        if token.startswith("sb_sk_"):
            return await self._authenticate_legacy_api_key(token, session)
        
        raise AuthenticationError(f"Invalid API key format")

    async def _authenticate_jwt(
        self, token: str, session: Optional[AsyncSession]
    ) -> AuthenticatedUser:
        """Validate a standard JWT."""
        try:
            payload = jwt_service.validate_access_token(token)
            
            if session:
                await self._verify_user_account(
                    payload["user_id"], payload["account_id"], session
                )

            return AuthenticatedUser(
                user_id=payload["user_id"],
                account_id=payload["account_id"],
                email=payload["email"],
                role=payload["role"],
                token_type=TokenType.JWT,
                groups=[],  # JWTs don't store groups currently, and we avoid DB hits
            )
        except (InvalidTokenError, TokenExpiredError) as e:
            raise AuthenticationError(str(e)) from e
        except Exception as e:
            logger.error("JWT authentication error", error=str(e))
            raise AuthenticationError("Invalid token") from e

    async def _verify_user_account(
        self, user_id: str, account_id: str, session: AsyncSession
    ) -> None:
        """Verify that a user belongs to an account."""
        # Special case: superadmins in system account
        if account_id == SYSTEM_ACCOUNT_ID:
            # We still want to verify the user exists and has a role, 
            # but they might be linked to the system account.
            pass

        result = await session.execute(
            select(UserModel.id).where(
                UserModel.id == user_id, UserModel.account_id == account_id
            )
        )
        if not result.scalar_one_or_none():
            logger.warning(
                "User-account mismatch detected",
                user_id=user_id,
                account_id=account_id
            )
            raise AuthenticationError("User does not belong to the specifying account")

    async def _authenticate_sb_token(
        self, token: str, session: Optional[AsyncSession]
    ) -> AuthenticatedUser:
        """Validate a SnackBase unified token (sb_ak, sb_pt, sb_ot)."""
        if not self.secret:
            from snackbase.core.config import get_settings
            secret = get_settings().token_secret
        else:
            secret = self.secret

        try:
            payload = TokenCodec.decode(token, secret)
            
            # Check expiration
            now = int(datetime.now(timezone.utc).timestamp())
            if payload.expires_at and payload.expires_at < now:
                raise AuthenticationError("Token has expired")

            # Check revocation if session is available
            if session:
                await self._check_revocation(payload.token_id, session)
                await self._verify_user_account(payload.user_id, payload.account_id, session)

            return AuthenticatedUser(
                user_id=payload.user_id,
                account_id=payload.account_id,
                email=payload.email,
                role=payload.role,
                token_type=payload.type,
                groups=[], # SB tokens currently don't store groups, or do they?
                           # PRD says "permissions", but not groups.
                           # We can load them from DB if needed.
            )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("SnackBase token authentication error", error=str(e))
            raise AuthenticationError("Invalid token") from e

    async def _authenticate_legacy_api_key(
        self, token: str, session: Optional[AsyncSession]
    ) -> AuthenticatedUser:
        """Validate a legacy API key (legacy sb_sk_ format)."""
        if not session:
            logger.warning("Legacy API key validation requires a database session")
            raise AuthenticationError("Authentication requires database session")

        key_hash = api_key_service.hash_key(token)
        
        # Load key and user
        result = await session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.key_hash == key_hash, APIKeyModel.is_active == True)
            .options(selectinload(APIKeyModel.user).selectinload(UserModel.groups), 
                     selectinload(APIKeyModel.user).selectinload(UserModel.role))
        )
        key_model = result.scalar_one_or_none()

        if not key_model:
            raise AuthenticationError("Invalid API key")

        # Check expiration (ensure comparison works even if DB returns naive datetime)
        if key_model.expires_at:
            expires_at = key_model.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                raise AuthenticationError("API key has expired")

        user = key_model.user
        if not user:
            raise AuthenticationError("User associated with API key not found")

        # Legacy keys are restricted to superadmins
        if user.account_id != SYSTEM_ACCOUNT_ID:
            logger.warning(
                "Legacy API key used by non-superadmin",
                user_id=user.id,
                account_id=user.account_id
            )
            raise AuthenticationError("API keys are restricted to superadmin users")

        # Update last_used_at
        key_model.last_used_at = datetime.now(timezone.utc)
        await session.commit()
        
        groups = [g.name for g in user.groups] if user.groups else []
        role_name = user.role.name if user.role else "admin"

        return AuthenticatedUser(
            user_id=user.id,
            account_id=user.account_id,
            email=user.email,
            role=role_name,
            token_type=TokenType.API_KEY,
            groups=groups,
        )

    async def _load_user_groups(self, user_id: str, session: AsyncSession) -> list[str]:
        """Load group names for a given user."""
        from snackbase.infrastructure.persistence.models import GroupModel, UsersGroupsModel
        
        result = await session.execute(
            select(GroupModel.name)
            .join(UsersGroupsModel)
            .where(UsersGroupsModel.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _check_revocation(self, token_id: str, session: AsyncSession) -> None:
        """Check if a token has been revoked."""
        from snackbase.infrastructure.persistence.models import TokenBlacklistModel

        result = await session.execute(
            select(TokenBlacklistModel.id).where(TokenBlacklistModel.id == token_id)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError("Token has been revoked")
