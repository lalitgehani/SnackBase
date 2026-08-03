"""Router for API key management.

Supports:
- Superadmin keys under the system account
- Account-admin service keys bound to the caller's account with approved scopes
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import (
    SYSTEM_ACCOUNT_ID,
    get_current_user,
)
from snackbase.infrastructure.api.schemas.api_key_schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyDetailResponse,
    APIKeyListItem,
    APIKeyListResponse,
)
from snackbase.infrastructure.auth import api_key_service
from snackbase.infrastructure.auth.token_types import AuthenticatedUser as AuthUser
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories import APIKeyRepository

router = APIRouter(tags=["API Keys"])
logger = get_logger(__name__)


def get_api_key_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIKeyRepository:
    """Get the API key repository."""
    return APIKeyRepository(session)


APIKeyRepo = Annotated[APIKeyRepository, Depends(get_api_key_repository)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


def _is_superadmin(user: AuthUser) -> bool:
    return user.account_id == SYSTEM_ACCOUNT_ID


def _is_account_admin(user: AuthUser) -> bool:
    return user.role == "admin" or _is_superadmin(user)


def _require_api_key_manager(user: AuthUser) -> None:
    """Account admins and superadmins may manage API keys for their own account."""
    if not _is_account_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account admin role required to manage API keys",
        )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APIKeyCreateResponse,
    summary="Create a new API key",
)
async def create_api_key(
    data: APIKeyCreateRequest,
    current_user: CurrentUser,
    api_key_repo: APIKeyRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIKeyCreateResponse:
    """Create an account-bound API key for the caller's account.

    Account administrators create service keys for their own account.
    Superadmins create keys bound to the system account. Scopes must be
    from the approved list (e.g. ``records:secrets:read``).
    """
    _require_api_key_manager(current_user)

    from snackbase.core.config import get_settings

    settings = get_settings()

    current_count = await api_key_repo.count_by_user(current_user.user_id)
    if current_count >= getattr(settings, "api_key_max_per_user", 10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum number of API keys reached "
                f"({getattr(settings, 'api_key_max_per_user', 10)})"
            ),
        )

    try:
        plaintext_key, created_key = await api_key_service.create_api_key(
            session=session,
            user_id=current_user.user_id,
            email=current_user.email,
            account_id=current_user.account_id,
            role=current_user.role,
            name=data.name,
            scopes=data.scopes,
            expires_at=data.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    await session.commit()

    logger.info(
        "API Key created",
        key_id=created_key.id,
        user_id=current_user.user_id,
        account_id=current_user.account_id,
        scopes=list(created_key.scopes or []),
    )

    return APIKeyCreateResponse(
        id=created_key.id,
        name=created_key.name,
        key=plaintext_key,
        expires_at=created_key.expires_at,
        created_at=created_key.created_at,
        scopes=list(created_key.scopes or []),
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="List API keys",
)
async def list_api_keys(
    current_user: CurrentUser,
    api_key_repo: APIKeyRepo,
) -> APIKeyListResponse:
    """List API keys owned by the current user within their account."""
    _require_api_key_manager(current_user)
    keys = await api_key_repo.list_all_by_user(current_user.user_id)

    return APIKeyListResponse(
        total=len(keys),
        items=[
            APIKeyListItem(
                id=key.id,
                name=key.name,
                key=api_key_service.mask_key(key.key_hash),
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                is_active=key.is_active,
                created_at=key.created_at,
                scopes=list(key.scopes or []),
            )
            for key in keys
        ],
    )


@router.get(
    "/{key_id}",
    response_model=APIKeyDetailResponse,
    summary="Get API key details",
)
async def get_api_key(
    key_id: str,
    current_user: CurrentUser,
    api_key_repo: APIKeyRepo,
) -> APIKeyDetailResponse:
    """Get details for a specific API key owned by the current user."""
    _require_api_key_manager(current_user)
    key = await api_key_repo.get_by_id(key_id)

    if (
        not key
        or key.user_id != current_user.user_id
        or key.account_id != current_user.account_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKeyDetailResponse(
        id=key.id,
        name=key.name,
        key=api_key_service.mask_key(key.key_hash),
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        is_active=key.is_active,
        created_at=key.created_at,
        updated_at=key.updated_at,
        scopes=list(key.scopes or []),
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
)
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUser,
    api_key_repo: APIKeyRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Revoke (soft delete) an API key owned by the current user."""
    _require_api_key_manager(current_user)
    key = await api_key_repo.get_by_id(key_id)

    if (
        not key
        or key.user_id != current_user.user_id
        or key.account_id != current_user.account_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await api_key_service.revoke_api_key(
        token_id=key.id,
        session=session,
        reason=f"Revoked by user {current_user.user_id}",
    )

    await api_key_repo.soft_delete(key_id)
    await session.commit()

    logger.info(
        "API Key revoked",
        key_id=key_id,
        user_id=current_user.user_id,
        account_id=current_user.account_id,
    )
