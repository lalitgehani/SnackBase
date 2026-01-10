"""Authentication API routes.

Provides endpoints for user registration, login, and token management.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services import (
    AccountCodeGenerator,
    SlugGenerator,
    default_password_validator,
)
from snackbase.domain.services.email_verification_service import EmailVerificationService
from snackbase.domain.services.password_reset_service import PasswordResetService
from snackbase.infrastructure.api.dependencies import (
    AuthenticatedUser,
    CurrentUser,
    get_password_reset_service,
    get_verification_service,
)
from snackbase.infrastructure.api.schemas import (
    AccountResponse,
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegistrationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SendVerificationRequest,
    TokenRefreshResponse,
    UserResponse,
    VerifyEmailRequest,
    VerifyResetTokenResponse,
)
from snackbase.infrastructure.auth import (
    DUMMY_PASSWORD_HASH,
    InvalidTokenError,
    TokenExpiredError,
    hash_password,
    jwt_service,
    verify_password,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    GroupModel,
    RefreshTokenModel,
    UserModel,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    GroupRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from snackbase.domain.services.pii_masking_service import PIIMaskingService

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegistrationResponse,
    responses={
        400: {"description": "Validation error"},
        409: {"description": "Conflict - email or slug already exists"},
    },
)
async def register(
    register_request: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    verification_service: EmailVerificationService = Depends(get_verification_service),
) -> RegistrationResponse | JSONResponse:
    """Register a new account and user.

    Creates a new account with the provided details and creates the first user
    as an admin. Returns a success message instructing the user to verify their email.

    Flow:
    1. Validate password strength
    2. Generate or validate account slug
    3. Check slug uniqueness
    4. Generate account ID
    5. Hash password
    6. Create account record
    7. Create user record with 'admin' role
    8. Send verification email
    9. Return response (no tokens)
    """
    # 1. Validate password strength
    password_errors = default_password_validator.validate(register_request.password)
    if password_errors:
        logger.info(
            "Registration failed: password validation",
            email=register_request.email,
            error_count=len(password_errors),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "details": [
                    {"field": e.field, "message": e.message, "code": e.code}
                    for e in password_errors
                ],
            },
        )

    # 2. Generate or validate account slug
    if register_request.account_slug:
        slug = register_request.account_slug.lower()
        slug_errors = SlugGenerator.validate(slug)
        if slug_errors:
            logger.info(
                "Registration failed: slug validation",
                email=register_request.email,
                slug=slug,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "details": [
                        {"field": e.field, "message": e.message, "code": e.code}
                        for e in slug_errors
                    ],
                },
            )
    else:
        slug = SlugGenerator.generate(register_request.account_name)

    # Initialize repositories
    account_repo = AccountRepository(session)
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)

    # 3. Check slug uniqueness
    if await account_repo.slug_exists(slug):
        logger.info(
            "Registration failed: slug exists",
            email=register_request.email,
            slug=slug,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Conflict",
                "message": "An account with this slug already exists",
                "field": "account_slug",
            },
        )

    # 4. Generate account ID and code
    existing_codes = await account_repo.get_all_account_codes()
    account_id = str(uuid.uuid4())  # Generate UUID
    account_code = AccountCodeGenerator.generate(existing_codes)  # Generate code

    # 5. Hash password
    password_hash = hash_password(register_request.password)

    # 6. Create account record
    account = AccountModel(
        id=account_id,
        account_code=account_code,
        slug=slug,
        name=register_request.account_name,
    )
    await account_repo.create(account)

    # 7. Create user record with 'admin' role
    admin_role = await role_repo.get_by_name("admin")
    if admin_role is None:
        logger.error("Admin role not found in database")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Role configuration error"},
        )

    user = UserModel(
        id=str(uuid.uuid4()),
        account_id=account_id,
        email=register_request.email,
        password_hash=password_hash,
        role_id=admin_role.id,
        is_active=True,
        email_verified=False,  # Explicitly set to False
    )
    await user_repo.create(user)

    # 7.5. Create pii_access group and add user to it
    group_repo = GroupRepository(session)
    pii_group = GroupModel(
        id=str(uuid.uuid4()),
        account_id=account_id,
        name=PIIMaskingService.PII_ACCESS_GROUP,  # "pii_access"
        description="Users in this group can view unmasked PII data",
    )
    await group_repo.create(pii_group)
    await group_repo.add_user(group_id=pii_group.id, user_id=user.id)

    logger.info(
        "pii_access group created and user added",
        account_id=account_id,
        group_id=pii_group.id,
        user_id=user.id,
    )

    # Commit the transaction
    await session.commit()

    # Refresh to get updated timestamps
    await session.refresh(account)
    await session.refresh(user)

    logger.info(
        "Account registered successfully",
        account_id=account_id,
        slug=slug,
        user_email=register_request.email,
    )

    # 8. Send verification email
    try:
        await verification_service.send_verification_email(
            user_id=user.id,
            email=user.email,
            account_id=account.id,
        )
    except Exception as e:
        logger.error(
            "Failed to send initial verification email during registration",
            error=str(e),
            user_id=user.id,
        )
        # Even if email fails, we return success so user can request resend later if needed
        # Or ideally, we might want to warn them, but for now standard success with email hint is fine

    # 9. Return response (no tokens)
    return RegistrationResponse(
        message="Registration successful. Please check your email to verify your account.",
        account=AccountResponse(
            id=account.id,
            slug=account.slug,
            name=account.name,
            created_at=account.created_at,
        ),
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=admin_role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=AuthResponse,
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse | JSONResponse:
    """Authenticate a user and return JWT tokens.

    Validates the user's credentials against the specified account and returns
    JWT tokens for authenticated access.

    Flow:
    1. Resolve account by slug or ID
    2. Look up user by email in account
    3. Check authentication provider (OAuth/SAML users must use their respective flows)
    4. Verify password using timing-safe comparison
    5. Check if user is active
    6. Update last_login timestamp
    7. Generate JWT tokens
    8. Return response

    Security:
    - All authentication failures return the same generic 401 message
    - Password verification is always performed (even with dummy hash) to prevent timing attacks
    """
    # Generic error response for all auth failures (prevents user enumeration)
    auth_error = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Authentication failed",
            "message": "Invalid credentials",
        },
    )

    # Initialize repositories
    account_repo = AccountRepository(session)
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)

    # 1. Resolve account by slug or ID
    account = await account_repo.get_by_slug_or_code(request.account)

    if account is None:
        # Account not found - still verify password to prevent timing attacks
        logger.info(
            "Login failed: account not found",
            account_identifier=request.account,
            email=request.email,
        )
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        return auth_error

    # 2. Look up user by email in account
    user = await user_repo.get_by_email_and_account(request.email, account.id)

    if user is None:
        # User not found - still verify password to prevent timing attacks
        logger.info(
            "Login failed: user not found in account",
            account_id=account.id,
            email=request.email,
        )
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        return auth_error

    # 3. Check authentication provider
    # Users with OAuth or SAML must use their respective authentication flows
    if user.auth_provider != "password":
        # Still verify password to maintain constant-time behavior (prevent timing attacks)
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        
        logger.info(
            "Login failed: wrong authentication method",
            account_id=account.id,
            user_id=user.id,
            auth_provider=user.auth_provider,
            provider_name=user.auth_provider_name,
        )
        
        # Determine the correct authentication URL based on provider type
        if user.auth_provider == "oauth":
            provider_name = user.auth_provider_name or "oauth"
            redirect_url = f"/api/v1/auth/oauth/{provider_name}/authorize"
            message = f"This account uses OAuth authentication. Please use the OAuth login flow."
        elif user.auth_provider == "saml":
            provider_name = user.auth_provider_name or "saml"
            redirect_url = f"/api/v1/auth/saml/{provider_name}/login"
            message = f"This account uses SAML authentication. Please use the SAML SSO flow."
        else:
            # Unknown provider type - return generic error
            redirect_url = None
            message = f"This account uses {user.auth_provider} authentication. Please use the correct login method."
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Wrong authentication method",
                "message": message,
                "auth_provider": user.auth_provider,
                "provider_name": user.auth_provider_name,
                "redirect_url": redirect_url,
            },
        )

    # 4. Verify password using timing-safe comparison
    if not verify_password(request.password, user.password_hash):
        logger.info(
            "Login failed: invalid password",
            account_id=account.id,
            user_id=user.id,
        )
        return auth_error

    # 5. Check if user is active
    if not user.is_active:
        logger.info(
            "Login failed: user inactive",
            account_id=account.id,
            user_id=user.id,
        )
        return auth_error

    # 5.5. Check if email is verified
    if not user.email_verified:
        logger.info(
            "Login failed: email not verified",
            account_id=account.id,
            user_id=user.id,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication failed",
                "message": "Email not verified. Please check your email inbox.",
            },
        )

    # Get user's role
    role = await role_repo.get_by_id(user.role_id)
    if role is None:
        logger.error(
            "Login failed: role not found",
            account_id=account.id,
            user_id=user.id,
            role_id=user.role_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Role configuration error"},
        )

    # 6. Update last_login timestamp
    await user_repo.update_last_login(user.id)
    await session.commit()

    # Refresh to get updated timestamps
    await session.refresh(user)

    logger.info(
        "User logged in successfully",
        account_id=account.id,
        user_id=user.id,
        email=user.email,
    )

    # 7. Generate JWT tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=account.id,
        email=user.email,
        role=role.name,
    )
    refresh_token, token_id = jwt_service.create_refresh_token(
        user_id=user.id,
        account_id=account.id,
    )
    expires_in = jwt_service.get_expires_in()

    # Store refresh token in database for revocation tracking
    settings = get_settings()
    refresh_token_repo = RefreshTokenRepository(session)
    refresh_token_model = RefreshTokenModel(
        id=token_id,
        token_hash=refresh_token_repo.hash_token(refresh_token),
        user_id=user.id,
        account_id=account.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    await refresh_token_repo.create(refresh_token_model)
    await session.commit()

    # 8. Return response
    return AuthResponse(
        token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        account=AccountResponse(
            id=account.id,
            slug=account.slug,
            name=account.name,
            created_at=account.created_at,
        ),
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenRefreshResponse,
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_tokens(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenRefreshResponse | JSONResponse:
    """Refresh access and refresh tokens.

    Validates the provided refresh token, issues new tokens, and invalidates
    the old refresh token (token rotation).

    Flow:
    1. Validate refresh token (signature, expiration, type)
    2. Check if token is revoked in database
    3. Get user information from token claims
    4. Revoke old refresh token
    5. Generate new access token and refresh token
    6. Store new refresh token
    7. Return new tokens
    """
    auth_error = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Authentication failed",
            "message": "Invalid or expired refresh token",
        },
    )

    # 1. Validate refresh token
    try:
        payload = jwt_service.validate_refresh_token(request.refresh_token)
    except TokenExpiredError:
        logger.info("Token refresh failed: token expired")
        return auth_error
    except InvalidTokenError as e:
        logger.info("Token refresh failed: invalid token", error=str(e))
        return auth_error

    # 2. Check if token is revoked in database
    refresh_token_repo = RefreshTokenRepository(session)
    token_model = await refresh_token_repo.get_by_hash(request.refresh_token)

    if token_model is None:
        logger.info("Token refresh failed: token not found in database")
        return auth_error

    if token_model.is_revoked:
        logger.warning(
            "Token refresh failed: token already revoked",
            token_id=token_model.id,
            user_id=token_model.user_id,
        )
        return auth_error

    # 3. Get user information to generate new tokens
    user_id = payload["user_id"]
    account_id = payload["account_id"]

    # Get user's role for new access token
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)

    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        logger.info(
            "Token refresh failed: user not found or inactive",
            user_id=user_id,
        )
        return auth_error

    role = await role_repo.get_by_id(user.role_id)
    if role is None:
        logger.error(
            "Token refresh failed: role not found",
            user_id=user_id,
            role_id=user.role_id,
        )
        return auth_error

    # 4. Revoke old refresh token
    await refresh_token_repo.revoke(token_model.id)

    # 5. Generate new tokens
    access_token = jwt_service.create_access_token(
        user_id=user_id,
        account_id=account_id,
        email=user.email,
        role=role.name,
    )
    new_refresh_token, new_token_id = jwt_service.create_refresh_token(
        user_id=user_id,
        account_id=account_id,
    )
    expires_in = jwt_service.get_expires_in()

    # 6. Store new refresh token
    settings = get_settings()
    new_token_model = RefreshTokenModel(
        id=new_token_id,
        token_hash=refresh_token_repo.hash_token(new_refresh_token),
        user_id=user_id,
        account_id=account_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    await refresh_token_repo.create(new_token_model)
    await session.commit()

    logger.info(
        "Tokens refreshed successfully",
        user_id=user_id,
        account_id=account_id,
    )

    # 7. Return new tokens
    return TokenRefreshResponse(
        token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_current_user_info(
    current_user: AuthenticatedUser,
) -> dict:
    """Get the current authenticated user's information.

    This is a protected endpoint that requires a valid access token.
    Returns the user information extracted from the JWT token claims.
    """
    return {
        "user_id": current_user.user_id,
        "account_id": current_user.account_id,
        "email": current_user.email,
        "role": current_user.role,
    }


@router.post(
    "/send-verification",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Verification email sent"},
        401: {"description": "Not authenticated"},
        500: {"description": "Failed to send email"},
    },
)
async def send_verification_email(
    request: SendVerificationRequest,
    current_user: AuthenticatedUser,
    verification_service: EmailVerificationService = Depends(get_verification_service),
) -> dict:
    """Send a verification email to the current user.

    Args:
        request: Optional email address.
        current_user: The authenticated user.
        verification_service: Verification service dependency.
    """
    # Use provided email or fall back to current user's email
    email = request.email or current_user.email

    success = await verification_service.send_verification_email(
        user_id=current_user.user_id,
        email=email,
        account_id=current_user.account_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {"message": f"Verification email sent to {email}"}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error during email sending"},
    },
)
async def resend_verification(
    request_data: SendVerificationRequest,
    user: AuthenticatedUser,
    verification_service: EmailVerificationService = Depends(get_verification_service),
):
    """Resend verification email to the user."""
    email = request_data.email or user.email
    await verification_service.send_verification_email(
        user_id=user.user_id,
        email=email,
        account_id=user.account_id,
    )
    return {"message": "Verification email resent successfully"}


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Email verified successfully"},
        400: {"description": "Invalid or expired token"},
    },
)
async def verify_email(
    request: VerifyEmailRequest,
    verification_service: EmailVerificationService = Depends(get_verification_service),
) -> dict:
    """Verify a user's email address using a token.

    Args:
        request: Verification token.
        verification_service: Verification service dependency.
    """
    user = await verification_service.verify_email(request.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    return {
        "message": "Email verified successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "email_verified": user.email_verified,
        }
    }


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    response_model=ForgotPasswordResponse,
    responses={
        200: {"description": "Password reset email sent (or email not found - same response)"},
    },
)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> ForgotPasswordResponse:
    """Initiate password reset flow.

    Generates a reset token and sends an email with reset instructions.
    Always returns 200 regardless of whether the email exists (security - don't reveal user existence).

    Args:
        request: Email and account identifier.
        session: Database session.
        reset_service: Password reset service dependency.

    Returns:
        Generic success message.
    """
    # Initialize repositories
    account_repo = AccountRepository(session)
    user_repo = UserRepository(session)

    # Resolve account by slug or ID
    account = await account_repo.get_by_slug_or_code(request.account)

    if account is None:
        # Account not found - return success anyway (don't reveal account existence)
        logger.info(
            "Password reset requested: account not found",
            account_identifier=request.account,
            email=request.email,
        )
        return ForgotPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )

    # Look up user by email in account
    user = await user_repo.get_by_email_and_account(request.email, account.id)

    if user is None:
        # User not found - return success anyway (don't reveal user existence)
        logger.info(
            "Password reset requested: user not found in account",
            account_id=account.id,
            email=request.email,
        )
        return ForgotPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )

    # Check authentication provider - only password auth users can reset password
    if user.auth_provider != "password":
        logger.info(
            "Password reset requested: wrong authentication method",
            account_id=account.id,
            user_id=user.id,
            auth_provider=user.auth_provider,
        )
        # Still return success (don't reveal auth method)
        return ForgotPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )

    # Send reset email
    try:
        await reset_service.send_reset_email(
            user_id=user.id,
            email=user.email,
            account_id=account.id,
        )
        logger.info(
            "Password reset email sent",
            account_id=account.id,
            user_id=user.id,
            email=user.email,
        )
    except Exception as e:
        logger.error(
            "Failed to send password reset email",
            error=str(e),
            user_id=user.id,
        )
        # Still return success (don't reveal email sending failure)

    return ForgotPasswordResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    response_model=ResetPasswordResponse,
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid, expired, or used token"},
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> ResetPasswordResponse:
    """Reset password using a valid reset token.

    Validates the token, updates the password, and invalidates all refresh tokens.

    Args:
        request: Reset token and new password.
        reset_service: Password reset service dependency.

    Returns:
        Success message.

    Raises:
        HTTPException: 400 if token is invalid, expired, or already used.
    """
    # Validate password strength
    password_errors = default_password_validator.validate(request.new_password)
    if password_errors:
        logger.info(
            "Password reset failed: password validation",
            error_count=len(password_errors),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation error",
                "details": [
                    {"field": e.field, "message": e.message, "code": e.code}
                    for e in password_errors
                ],
            },
        )

    # Reset password
    user = await reset_service.reset_password(request.token, request.new_password)

    if not user:
        logger.info("Password reset failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used reset token",
        )

    logger.info(
        "Password reset successfully",
        user_id=user.id,
        email=user.email,
    )

    return ResetPasswordResponse(
        message="Password reset successfully. You can now log in with your new password."
    )


@router.get(
    "/verify-reset-token/{token}",
    status_code=status.HTTP_200_OK,
    response_model=VerifyResetTokenResponse,
    responses={
        200: {"description": "Token validity status"},
    },
)
async def verify_reset_token(
    token: str,
    reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> VerifyResetTokenResponse:
    """Verify if a password reset token is valid without using it.

    Used by frontend to pre-validate the token before showing the reset form.

    Args:
        token: The reset token to verify.
        reset_service: Password reset service dependency.

    Returns:
        Token validity status and expiration time.
    """
    is_valid, expires_at = await reset_service.verify_reset_token(token)

    return VerifyResetTokenResponse(
        valid=is_valid,
        expires_at=expires_at,
    )

