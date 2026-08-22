"""Unified authentication for all SnackBase token types.

Implements the Authenticator class which handles:
- Standard JWT Bearer tokens
- Trusted-issuer (platform) JWT tokens (RS256/ES256)
- SnackBase tokens (sb_ak, sb_pt, sb_ot)
- Legacy API keys (sb_sk)
"""

from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth.api_key_service import api_key_service
from snackbase.infrastructure.auth.jwt_service import (
    InvalidTokenError,
    TokenExpiredError,
    jwt_service,
)
from snackbase.infrastructure.auth.password_hasher import generate_random_password, hash_password
from snackbase.infrastructure.auth.platform_jwks import get_platform_jwks_client
from snackbase.infrastructure.auth.token_codec import AuthenticationError, TokenCodec
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenType
from snackbase.infrastructure.persistence.models import APIKeyModel, RoleModel, UserModel

logger = get_logger(__name__)

# System account ID for superadmins (matches dependencies.py)
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

# The only snackbase_role a platform (trusted-issuer) principal may carry. Platform
# principals are instance operators; see _try_authenticate_platform_jwt.
PLATFORM_OPERATOR_ROLE = "admin"

# auth_provider stamped on JIT-provisioned platform users. Also the predicate that keeps
# a platform `sub` from ever resolving to a locally-created user.
PLATFORM_AUTH_PROVIDER = "platform"


class Authenticator:
    """Unified authentication for all token types."""

    def __init__(self, secret: str | None = None):
        """Initialize the authenticator.

        Args:
            secret: Secret key for SnackBase tokens. If not provided,
                    uses the one from settings via TokenCodec.
        """
        self.secret = secret

    async def authenticate(
        self, request_headers: dict[str, str], session: AsyncSession | None = None
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
        self, token: str, session: AsyncSession | None
    ) -> AuthenticatedUser:
        """Authenticate a Bearer token (JWT, platform JWT, or SB token)."""
        if token.startswith("sb_"):
            return await self._authenticate_sb_token(token, session)

        jwt_error: AuthenticationError | None = None
        try:
            return await self._authenticate_jwt(token, session)
        except AuthenticationError as exc:
            jwt_error = exc

        if self._should_try_platform_jwt(token):
            return await self._try_authenticate_platform_jwt(token, session)

        if jwt_error is not None:
            raise jwt_error
        raise AuthenticationError("Invalid token")

    def _should_try_platform_jwt(self, token: str) -> bool:
        """Return True when the token looks like a configured platform issuer JWT."""
        settings = get_settings()
        if not settings.platform_auth_enabled:
            return False

        try:
            header = jwt.get_unverified_header(token)
            unverified = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256", "ES256", "HS256"],
            )
        except jwt.InvalidTokenError:
            return False

        if unverified.get("iss") != settings.platform_issuer:
            return False

        alg = header.get("alg")
        if not isinstance(alg, str):
            return False

        return alg.upper() in {"RS256", "ES256", "HS256", "NONE"}

    async def _authenticate_api_key_header(
        self, token: str, session: AsyncSession | None
    ) -> AuthenticatedUser:
        """Authenticate from X-API-Key header (either SB API Key or Legacy Key)."""
        # SnackBase API keys start with 'sb_ak.'
        if token.startswith("sb_ak."):
            return await self._authenticate_sb_token(token, session)

        # Legacy API keys start with 'sb_sk_'
        if token.startswith("sb_sk_"):
            return await self._authenticate_legacy_api_key(token, session)

        raise AuthenticationError("Invalid API key format")

    async def _authenticate_jwt(
        self, token: str, session: AsyncSession | None
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
        except (InvalidTokenError, TokenExpiredError, AuthenticationError) as e:
            raise AuthenticationError(str(e)) from e
        except Exception as e:
            logger.error("JWT authentication error", error=str(e))
            raise AuthenticationError("Invalid token") from e

    async def _try_authenticate_platform_jwt(
        self, token: str, session: AsyncSession | None
    ) -> AuthenticatedUser:
        """Validate a trusted-issuer (platform) JWT when configured."""
        settings = get_settings()
        if not settings.platform_auth_enabled:
            raise AuthenticationError("Invalid token")

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid token") from exc

        alg = header.get("alg")
        if not isinstance(alg, str):
            raise AuthenticationError("Unsupported token algorithm")
        alg_upper = alg.upper()
        if alg_upper in {"HS256", "NONE"}:
            raise AuthenticationError("Unsupported token algorithm")
        if alg_upper not in {"RS256", "ES256"}:
            raise AuthenticationError("Unsupported token algorithm")

        try:
            unverified = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=[alg],
            )
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid token") from exc

        if unverified.get("iss") != settings.platform_issuer:
            raise AuthenticationError("Invalid token issuer")

        if session is None:
            raise AuthenticationError("Authentication requires database session")

        jwks_client = get_platform_jwks_client()
        if jwks_client is None:
            raise AuthenticationError("Invalid token")

        signing_key = jwks_client.get_signing_key(token)

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[alg_upper],
                audience=settings.platform_audience,
                issuer=settings.platform_issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid token") from exc

        now = int(datetime.now(UTC).timestamp())
        issued_at = int(payload["iat"])
        if now - issued_at > settings.platform_max_token_age_seconds:
            raise AuthenticationError("Token is too old")

        sub = payload.get("sub")
        email = payload.get(settings.platform_email_claim)
        role_name = payload.get(settings.platform_role_claim)
        if not sub or not email or not role_name:
            raise AuthenticationError("Token missing required claims")

        # A platform principal is the operator of this instance and is resolved into the
        # system account, where `require_superadmin` admits on account alone. Anything that
        # is not an instance admin therefore has no place to land: reject it here, before
        # any user row is created, rather than granting it superadmin by omission.
        if role_name != PLATFORM_OPERATOR_ROLE:
            logger.warning(
                "Platform token rejected: not an instance operator",
                sub=str(sub),
                role=str(role_name),
            )
            raise AuthenticationError("Platform access requires an instance administrator")

        user = await self._resolve_platform_user(
            session=session,
            user_id=str(sub),
            email=str(email),
            role_name=str(role_name),
        )

        await self._verify_user_account(user.id, user.account_id, session)

        return AuthenticatedUser(
            user_id=user.id,
            account_id=user.account_id,
            email=user.email,
            role=role_name,
            token_type=TokenType.PLATFORM,
            groups=[],
        )

    async def _resolve_platform_user(
        self,
        *,
        session: AsyncSession,
        user_id: str,
        email: str,
        role_name: str,
    ) -> UserModel:
        """Look up or just-in-time provision a platform-mapped user."""
        # The `sub` claim is an id minted by a different system, so it is only ever matched
        # against rows this path created. Without the provider predicate a `sub` that
        # collides with a local user's id would authenticate the caller as that user.
        from snackbase.domain.services.superadmin_service import SuperadminService

        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.auth_provider == PLATFORM_AUTH_PROVIDER,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.account_id != SYSTEM_ACCOUNT_ID:
                # Provisioned by an earlier build that placed platform principals in the
                # instance's tenant account. Reconcile in place, otherwise the operator
                # would silently lose Studio access after this upgrade.
                await SuperadminService.ensure_system_account_exists(session)
                logger.info(
                    "Migrating platform user to the system account",
                    user_id=existing.id,
                    from_account_id=existing.account_id,
                )
                existing.account_id = SYSTEM_ACCOUNT_ID
                await session.commit()
                await session.refresh(existing)
            return existing

        role_result = await session.execute(
            select(RoleModel).where(RoleModel.name == role_name)
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            raise AuthenticationError(f"Unknown role: {role_name}")

        # Platform principals operate the instance itself, so they belong to the system
        # account (SY0000) exactly as a self-hosted superadmin does. This is independent of
        # the instance's own tenancy, which is why multi-tenant instances work identically.
        await SuperadminService.ensure_system_account_exists(session)

        user = UserModel(
            id=user_id,
            account_id=SYSTEM_ACCOUNT_ID,
            email=email,
            password_hash=hash_password(generate_random_password()),
            role_id=role.id,
            is_active=True,
            auth_provider=PLATFORM_AUTH_PROVIDER,
            external_id=user_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

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
        self, token: str, session: AsyncSession | None
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
            now = int(datetime.now(UTC).timestamp())
            if payload.expires_at and payload.expires_at < now:
                raise AuthenticationError("Token has expired")

            # Check revocation if session is available
            scopes: list[str] = list(payload.scopes or [])
            api_key_id: str | None = None
            if session:
                await self._check_revocation(payload.token_id, session)
                await self._verify_user_account(payload.user_id, payload.account_id, session)
                # Prefer DB-stored scopes for API keys (source of truth after create).
                if payload.type == TokenType.API_KEY:
                    api_key_id = payload.token_id
                    db_scopes = await self._load_api_key_scopes(payload.token_id, session)
                    if db_scopes is not None:
                        scopes = db_scopes
                    # Update last_used_at for API keys
                    await self._touch_api_key(payload.token_id, session)

            return AuthenticatedUser(
                user_id=payload.user_id,
                account_id=payload.account_id,
                email=payload.email,
                role=payload.role,
                token_type=payload.type,
                groups=[],  # SB tokens currently don't store groups
                scopes=scopes,
                api_key_id=api_key_id,
            )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("SnackBase token authentication error", error=str(e))
            raise AuthenticationError("Invalid token") from e

    async def _authenticate_legacy_api_key(
        self, token: str, session: AsyncSession | None
    ) -> AuthenticatedUser:
        """Validate a legacy API key (legacy sb_sk_ format)."""
        if not session:
            logger.warning("Legacy API key validation requires a database session")
            raise AuthenticationError("Authentication requires database session")

        key_hash = api_key_service.hash_key(token)

        # Load key and user
        result = await session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.key_hash == key_hash, APIKeyModel.is_active.is_(True))
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
                expires_at = expires_at.replace(tzinfo=UTC)

            if expires_at < datetime.now(UTC):
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
        key_model.last_used_at = datetime.now(UTC)
        await session.commit()

        groups = [g.name for g in user.groups] if user.groups else []
        role_name = user.role.name if user.role else "admin"

        scopes = list(key_model.scopes or [])
        return AuthenticatedUser(
            user_id=user.id,
            account_id=user.account_id,
            email=user.email,
            role=role_name,
            token_type=TokenType.API_KEY,
            groups=groups,
            scopes=scopes,
            api_key_id=key_model.id,
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

    async def _load_api_key_scopes(
        self, token_id: str, session: AsyncSession
    ) -> list[str] | None:
        """Load scopes for an API key from the database.

        Returns:
            Scope list if the key row exists, None if not found.
        """
        result = await session.execute(
            select(APIKeyModel.scopes, APIKeyModel.is_active).where(APIKeyModel.id == token_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        scopes, is_active = row
        if not is_active:
            raise AuthenticationError("API key is inactive")
        return list(scopes or [])

    async def _touch_api_key(self, token_id: str, session: AsyncSession) -> None:
        """Update last_used_at for an API key without failing authentication."""
        try:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.id == token_id)
            )
            key_model = result.scalar_one_or_none()
            if key_model is not None:
                key_model.last_used_at = datetime.now(UTC)
                await session.commit()
        except Exception as e:
            logger.warning("Failed to update API key last_used_at", error=str(e))

    async def _check_revocation(self, token_id: str, session: AsyncSession) -> None:
        """Check if a token has been revoked."""
        from snackbase.infrastructure.persistence.models import TokenBlacklistModel

        result = await session.execute(
            select(TokenBlacklistModel.id).where(TokenBlacklistModel.id == token_id)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError("Token has been revoked")
