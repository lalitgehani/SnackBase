"""Authentication API routes.

Provides endpoints for user registration, login, and token management.
"""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import (
    AccountIdGenerator,
    SlugGenerator,
    default_password_validator,
)
from snackbase.infrastructure.api.schemas import (
    AccountResponse,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from snackbase.infrastructure.auth import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    jwt_service,
    verify_password,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import AccountModel, UserModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    RoleRepository,
    UserRepository,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    responses={
        400: {"description": "Validation error"},
        409: {"description": "Conflict - email or slug already exists"},
    },
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse | JSONResponse:
    """Register a new account and user.

    Creates a new account with the provided details and creates the first user
    as an admin. Returns JWT tokens for immediate authentication.

    Flow:
    1. Validate password strength
    2. Generate or validate account slug
    3. Check slug uniqueness
    4. Generate account ID
    5. Hash password
    6. Create account record
    7. Create user record with 'admin' role
    8. Generate JWT tokens
    9. Return response
    """
    # 1. Validate password strength
    password_errors = default_password_validator.validate(request.password)
    if password_errors:
        logger.info(
            "Registration failed: password validation",
            email=request.email,
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
    if request.account_slug:
        slug = request.account_slug.lower()
        slug_errors = SlugGenerator.validate(slug)
        if slug_errors:
            logger.info(
                "Registration failed: slug validation",
                email=request.email,
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
        slug = SlugGenerator.generate(request.account_name)

    # Initialize repositories
    account_repo = AccountRepository(session)
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)

    # 3. Check slug uniqueness
    if await account_repo.slug_exists(slug):
        logger.info(
            "Registration failed: slug exists",
            email=request.email,
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

    # 4. Generate account ID
    existing_ids = await account_repo.get_all_ids()
    account_id = AccountIdGenerator.generate(existing_ids)

    # 5. Hash password
    password_hash = hash_password(request.password)

    # 6. Create account record
    account = AccountModel(
        id=account_id,
        slug=slug,
        name=request.account_name,
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
        email=request.email,
        password_hash=password_hash,
        role_id=admin_role.id,
        is_active=True,
    )
    await user_repo.create(user)

    # Commit the transaction
    await session.commit()

    # Refresh to get updated timestamps
    await session.refresh(account)
    await session.refresh(user)

    logger.info(
        "Account registered successfully",
        account_id=account_id,
        slug=slug,
        user_email=request.email,
    )

    # 8. Generate JWT tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=account_id,
        email=user.email,
        role=admin_role.name,
    )
    refresh_token = jwt_service.create_refresh_token(
        user_id=user.id,
        account_id=account_id,
    )
    expires_in = jwt_service.get_expires_in()

    # 9. Return response
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
    3. Verify password using timing-safe comparison
    4. Check if user is active
    5. Update last_login timestamp
    6. Generate JWT tokens
    7. Return response

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
    account = await account_repo.get_by_slug_or_id(request.account)

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

    # 3. Verify password using timing-safe comparison
    if not verify_password(request.password, user.password_hash):
        logger.info(
            "Login failed: invalid password",
            account_id=account.id,
            user_id=user.id,
        )
        return auth_error

    # 4. Check if user is active
    if not user.is_active:
        logger.info(
            "Login failed: user inactive",
            account_id=account.id,
            user_id=user.id,
        )
        return auth_error

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

    # 5. Update last_login timestamp
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

    # 6. Generate JWT tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=account.id,
        email=user.email,
        role=role.name,
    )
    refresh_token = jwt_service.create_refresh_token(
        user_id=user.id,
        account_id=account.id,
    )
    expires_in = jwt_service.get_expires_in()

    # 7. Return response
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

