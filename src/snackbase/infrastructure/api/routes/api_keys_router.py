"""Router for API key management.

Superadmin-only endpoints for managing persistent API keys.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import (
    SuperadminUser,
    get_db_session,
    require_superadmin,
)
from snackbase.infrastructure.api.schemas.api_key_schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyDetailResponse,
    APIKeyListItem,
    APIKeyListResponse,
)
from snackbase.infrastructure.auth import api_key_service
from snackbase.infrastructure.persistence.models import APIKeyModel
from snackbase.infrastructure.persistence.repositories import APIKeyRepository

router = APIRouter(tags=["API Keys"])
logger = get_logger(__name__)


def get_api_key_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIKeyRepository:
    """Get the API key repository."""
    return APIKeyRepository(session)


APIKeyRepo = Annotated[APIKeyRepository, Depends(get_api_key_repository)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APIKeyCreateResponse,
    summary="Create a new API key",
)
async def create_api_key(
    data: APIKeyCreateRequest,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    api_key_repo: APIKeyRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIKeyCreateResponse:
    """Create a new superadmin API key.

    Returns the full plaintext key which will NEVER be shown again.
    Store it securely.
    """
    # Check max keys limit
    from snackbase.core.config import get_settings
    settings = get_settings()
    
    current_count = await api_key_repo.count_by_user(current_user.user_id)
    if current_count >= getattr(settings, "api_key_max_per_user", 10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of API keys reached ({getattr(settings, 'api_key_max_per_user', 10)})",
        )

    # Generate and store key using the redesigned service
    plaintext_key, created_key = await api_key_service.create_api_key(
        session=session,
        user_id=current_user.user_id,
        email=current_user.email,
        account_id=current_user.account_id,
        role=current_user.role,
        name=data.name,
        expires_at=data.expires_at,
    )
    
    # The service already flushes, but we need to commit (router handles it)
    await session.commit()
    
    logger.info(
        "API Key created",
        key_id=created_key.id,
        user_id=current_user.user_id,
        name=data.name,
    )
    
    return APIKeyCreateResponse(
        id=created_key.id,
        name=created_key.name,
        key=plaintext_key,
        expires_at=created_key.expires_at,
        created_at=created_key.created_at,
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="List API keys",
)
async def list_api_keys(
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    api_key_repo: APIKeyRepo,
) -> APIKeyListResponse:
    """List all API keys for the current superadmin user."""
    keys = await api_key_repo.list_all_by_user(current_user.user_id)
    
    return APIKeyListResponse(
        total=len(keys),
        items=[
            APIKeyListItem(
                id=key.id,
                name=key.name,
                key=api_key_service.mask_key(key.key_hash), # We store hash, so mask based on hash
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                is_active=key.is_active,
                created_at=key.created_at,
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
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    api_key_repo: APIKeyRepo,
) -> APIKeyDetailResponse:
    """Get details for a specific API key."""
    key = await api_key_repo.get_by_id(key_id)
    
    if not key or key.user_id != current_user.user_id:
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
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
)
async def revoke_api_key(
    key_id: str,
    current_user: Annotated[SuperadminUser, Depends(require_superadmin)],
    api_key_repo: APIKeyRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Revoke (soft delete) an API key."""
    key = await api_key_repo.get_by_id(key_id)
    
    if not key or key.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
        
    # Add to blacklist using the service
    await api_key_service.revoke_api_key(
        token_id=key.id,
        session=session,
        reason=f"Revoked by user {current_user.user_id}",
    )

    # Also mark as inactive in the main table
    await api_key_repo.soft_delete(key_id)
    await session.commit()
    
    logger.info(
        "API Key revoked",
        key_id=key_id,
        user_id=current_user.user_id,
    )
