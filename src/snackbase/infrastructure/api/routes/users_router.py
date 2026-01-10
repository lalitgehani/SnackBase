"""Router for user management.

Superadmin-only endpoints for managing users across all accounts.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services.email_verification_service import EmailVerificationService
from snackbase.domain.services.password_reset_service import PasswordResetService
from snackbase.domain.services.password_validator import default_password_validator
from snackbase.infrastructure.api.dependencies import (
    SuperadminUser,
    get_db_session,
    get_password_reset_service,
    get_verification_service,
    require_superadmin,
)
from snackbase.infrastructure.api.schemas.users_schemas import (
    PasswordResetRequest,
    UserCreateRequest,
    UserListItem,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from snackbase.infrastructure.auth import generate_random_password, hash_password
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.repositories.user_repository import UserRepository

router = APIRouter(tags=["Users"])
logger = get_logger(__name__)


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    """Get the user repository."""
    return UserRepository(session)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    user_data: UserCreateRequest,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """Create a new user in any account (superadmin only).

    Creates a user with the specified email, password, account, and role.
    For password-based users, the password must meet security requirements.
    For OAuth/SAML users, a random unknowable password is auto-generated.
    """
    # Determine password based on auth provider
    if user_data.auth_provider != "password":
        # OAuth/SAML users get a random unknowable password
        password = generate_random_password()
        logger.info(
            "oauth_user_creation",
            email=user_data.email,
            auth_provider=user_data.auth_provider,
            auth_provider_name=user_data.auth_provider_name,
            message="Generated random password for OAuth/SAML user",
        )
    else:
        # Password-based users: require password and validate strength
        if user_data.password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for password-based authentication",
            )
        password = user_data.password.get_secret_value()
        password_errors = default_password_validator.validate(password)
        if password_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation error",
                    "details": [
                        {
                            "field": error.field,
                            "message": error.message,
                            "code": error.code,
                        }
                        for error in password_errors
                    ],
                },
            )

    # Verify account exists
    account = await session.get(AccountModel, user_data.account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Verify role exists
    role = await session.get(RoleModel, user_data.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check email uniqueness within account
    if await user_repo.email_exists_in_account(user_data.email, user_data.account_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in the account",
        )

    # Create user
    new_user = UserModel(
        id=str(uuid.uuid4()),
        account_id=user_data.account_id,
        email=user_data.email,
        password_hash=hash_password(password),
        role_id=user_data.role_id,
        is_active=user_data.is_active,
        auth_provider=user_data.auth_provider,
        auth_provider_name=user_data.auth_provider_name,
        external_id=user_data.external_id,
        external_email=user_data.external_email,
        profile_data=user_data.profile_data,
    )

    created_user = await user_repo.create(new_user)
    await session.commit()

    return UserResponse(
        id=created_user.id,
        email=created_user.email,
        account_id=created_user.account_id,
        account_code=account.account_code,
        account_name=account.name,
        role_id=created_user.role_id,
        role_name=role.name,
        is_active=created_user.is_active,
        auth_provider=created_user.auth_provider,
        auth_provider_name=created_user.auth_provider_name,
        external_id=created_user.external_id,
        external_email=created_user.external_email,
        profile_data=created_user.profile_data,
        email_verified=created_user.email_verified,
        email_verified_at=created_user.email_verified_at,
        created_at=created_user.created_at,
        last_login=created_user.last_login,
    )


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
)
async def list_users(
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    account_id: str | None = Query(None, description="Filter by account ID"),
    role_id: int | None = Query(None, description="Filter by role ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by email"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of records to return"),
    sort: str = Query("-created_at", description="Sort field with +/- prefix"),
) -> UserListResponse:
    """List users with optional filters (superadmin only).

    Returns a paginated list of users across all accounts.
    Supports filtering by account, role, status, and email search.
    """
    # Parse sort parameter
    sort_field = sort.lstrip("+-")
    sort_desc = sort.startswith("-")

    users, total = await user_repo.list_paginated(
        account_id=account_id,
        role_id=role_id,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
        sort_field=sort_field,
        sort_desc=sort_desc,
    )

    return UserListResponse(
        total=total,
        items=[
            UserListItem(
                id=user.id,
                email=user.email,
                account_id=user.account_id,
                account_code=user.account.account_code,
                account_name=user.account.name,
                role_id=user.role_id,
                role_name=user.role.name,
                is_active=user.is_active,
                auth_provider=user.auth_provider,
                auth_provider_name=user.auth_provider_name,
                external_id=user.external_id,
                external_email=user.external_email,
                profile_data=user.profile_data,
                email_verified=user.email_verified,
                email_verified_at=user.email_verified_at,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            for user in users
        ],
    )


@router.get(
    "/{user_id}",
    summary="Get a user",
)
async def get_user(
    user_id: str,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """Get a specific user by ID (superadmin only)."""
    # Get user with relationships loaded
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserModel)
        .where(UserModel.id == user_id)
        .options(selectinload(UserModel.account), selectinload(UserModel.role))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        account_id=user.account_id,
        account_code=user.account.account_code,
        account_name=user.account.name,
        role_id=user.role_id,
        role_name=user.role.name,
        is_active=user.is_active,
        auth_provider=user.auth_provider,
        auth_provider_name=user.auth_provider_name,
        external_id=user.external_id,
        external_email=user.external_email,
        profile_data=user.profile_data,
        email_verified=user.email_verified,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.patch(
    "/{user_id}",
    summary="Update a user",
)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """Update a user's email, role, or active status (superadmin only).

    Cannot modify password through this endpoint - use the password reset endpoint.
    Cannot modify your own role or deactivate yourself.
    """
    # Prevent self-modification
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own account through this endpoint",
        )

    # Get user with relationships
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserModel)
        .where(UserModel.id == user_id)
        .options(selectinload(UserModel.account), selectinload(UserModel.role))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update email if provided
    if user_data.email is not None:
        # Check email uniqueness if changing email
        if user_data.email != user.email:
            if await user_repo.email_exists_in_account(user_data.email, user.account_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists in the account",
                )
        user.email = user_data.email

    # Update role if provided
    if user_data.role_id is not None:
        # Verify role exists
        role = await session.get(RoleModel, user_data.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )
        user.role_id = user_data.role_id

    # Update active status if provided
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    # Update auth provider fields if provided
    if user_data.auth_provider is not None:
        user.auth_provider = user_data.auth_provider
    if user_data.auth_provider_name is not None:
        user.auth_provider_name = user_data.auth_provider_name
    if user_data.external_id is not None:
        user.external_id = user_data.external_id
    if user_data.external_email is not None:
        user.external_email = user_data.external_email
    if user_data.profile_data is not None:
        user.profile_data = user_data.profile_data

    updated_user = await user_repo.update(user)
    await session.commit()

    # Reload relationships to get fresh data
    await session.refresh(updated_user, ["account", "role"])

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        account_id=updated_user.account_id,
        account_code=updated_user.account.account_code,
        account_name=updated_user.account.name,
        role_id=updated_user.role_id,
        role_name=updated_user.role.name,
        is_active=updated_user.is_active,
        auth_provider=updated_user.auth_provider,
        auth_provider_name=updated_user.auth_provider_name,
        external_id=updated_user.external_id,
        external_email=updated_user.external_email,
        profile_data=updated_user.profile_data,
        email_verified=updated_user.email_verified,
        email_verified_at=updated_user.email_verified_at,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login,
    )


@router.put(
    "/{user_id}/password",
    status_code=status.HTTP_200_OK,
    summary="Reset user password",
)
async def reset_user_password(
    user_id: str,
    password_data: PasswordResetRequest,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    reset_service: Annotated[PasswordResetService, Depends(get_password_reset_service)],
) -> dict[str, str]:
    """Reset a user's password (superadmin only).

    Can either send a reset link email or set a new password directly.
    Invalidates all of the user's refresh tokens, forcing them to log in again.
    """
    # Get user
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if password_data.send_reset_link:
        # Mode 1: Send reset link
        success = await reset_service.send_reset_link_by_admin(
            user_id=user.id,
            email=user.email,
            account_id=user.account_id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email",
            )
        
        logger.info(
            "password_reset_link_sent",
            user_id=user_id,
            reset_by=current_user.user_id,
        )
        return {"message": f"Password reset link sent to {user.email}"}

    # Mode 2: Set password directly
    # Validate password strength
    password = password_data.new_password.get_secret_value()
    password_errors = default_password_validator.validate(password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation error",
                "details": [
                    {
                        "field": error.field,
                        "message": error.message,
                        "code": error.code,
                    }
                    for error in password_errors
                ],
            },
        )

    # Use service to set password (handles refresh token revocation and reset token cleanup)
    await reset_service.set_password_by_admin(user_id, password)

    logger.info(
        "password_reset",
        user_id=user_id,
        reset_by=current_user.user_id,
    )

    return {"message": "Password updated successfully"}


@router.post(
    "/{user_id}/verify",
    status_code=status.HTTP_200_OK,
    summary="Manually verify user email",
)
async def verify_user_email(
    user_id: str,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Manually mark a user's email as verified (superadmin only).
    
    This bypasses the email token flow and directly updates the user's status.
    """
    # Get user
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        return {"message": "User email is already verified"}

    # Update verification status
    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await user_repo.update(user)
    await session.commit()

    logger.info(
        "user_manually_verified",
        user_id=user_id,
        verified_by=current_user.user_id,
    )

    return {"message": "User email verified successfully"}


@router.post(
    "/{user_id}/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend verification email",
)
async def resend_user_verification(
    user_id: str,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    verification_service: Annotated[EmailVerificationService, Depends(get_verification_service)],
) -> dict[str, str]:
    """Resend verification email to a user (superadmin only)."""
    # Get user
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email is already verified",
        )

    # Send verification email
    success = await verification_service.send_verification_email(
        user_id=user.id,
        email=user.email,
        account_id=user.account_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    logger.info(
        "verification_email_resent_by_admin",
        user_id=user_id,
        resent_by=current_user.user_id,
    )

    return {"message": f"Verification email sent to {user.email}"}


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user",
)
async def deactivate_user(
    user_id: str,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    user_repo: UserRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Deactivate a user (soft delete via is_active flag) (superadmin only).

    The user will not be able to log in, but their data is preserved.
    You cannot deactivate yourself.
    """
    # Prevent self-deactivation
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate your own account",
        )

    # Check if user exists
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Soft delete (set is_active=False)
    await user_repo.soft_delete(user_id)
    await session.commit()

    logger.info(
        "user_deactivated",
        user_id=user_id,
        deactivated_by=current_user.user_id,
    )
