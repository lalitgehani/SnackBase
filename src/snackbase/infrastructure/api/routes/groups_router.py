"""Router for group management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services.permission_cache import PermissionCache
from snackbase.infrastructure.api.dependencies import (
    AuthenticatedUser,
    get_db_session,
    get_permission_cache,
    require_superadmin,
    SYSTEM_ACCOUNT_ID,
)
from snackbase.infrastructure.api.schemas.group_schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    UserGroupUpdate,
)
from snackbase.infrastructure.persistence.models import GroupModel
from snackbase.infrastructure.persistence.repositories.group_repository import GroupRepository

router = APIRouter(tags=["Groups"])
logger = get_logger(__name__)


def get_group_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    permission_cache: Annotated[PermissionCache, Depends(get_permission_cache)],
) -> GroupRepository:
    """Get the group repository."""
    return GroupRepository(session, permission_cache)


GroupRepo = Annotated[GroupRepository, Depends(get_group_repository)]


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group",
)
async def create_group(
    group_data: GroupCreate,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GroupModel:
    """Create a new group in the user's account.

    Requires authenticated user (usually admin, but enforced via permissions logic if needed).
    For now, any authenticated user can create groups in their account (or restrict to admin).
    """
    # Determine account_id: use provided account_id if superadmin, otherwise use current user's account
    target_account_id = group_data.account_id if group_data.account_id else current_user.account_id
    
    # Check uniqueness
    existing = await group_repo.get_by_name_and_account(
        group_data.name, target_account_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group with this name already exists in the account",
        )

    new_group = GroupModel(
        id=str(uuid.uuid4()),
        account_id=target_account_id,
        name=group_data.name,
        description=group_data.description,
    )

    result = await group_repo.create(new_group)
    await session.commit()
    return result


@router.get(
    "",
    response_model=list[GroupResponse],
    summary="List groups",
)
async def list_groups(
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    skip: int = 0,
    limit: int = 100,
) -> list[GroupModel]:
    """List all groups in the user's account (or all groups if superadmin)."""
    # Superadmins see all groups across all accounts
    if current_user.account_id == SYSTEM_ACCOUNT_ID:
        return await group_repo.list_all(skip, limit)
    # Regular users see only groups in their account
    return await group_repo.list(current_user.account_id, skip, limit)


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Get a group",
)
async def get_group(
    group_id: str,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
) -> GroupModel:
    """Get a specific group by ID."""
    group = await group_repo.get_by_id(group_id)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Ensure account isolation (skip for superadmins)
    if current_user.account_id != SYSTEM_ACCOUNT_ID and group.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    return group


@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Update a group",
)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GroupModel:
    """Update a group."""
    group = await group_repo.get_by_id(group_id)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Ensure account isolation (skip for superadmins)
    if current_user.account_id != SYSTEM_ACCOUNT_ID and group.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Check name uniqueness if changing name
    if group_data.name and group_data.name != group.name:
        existing = await group_repo.get_by_name_and_account(
            group_data.name, current_user.account_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Group with this name already exists in the account",
            )
            
    if group_data.name:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
        
    result = await group_repo.update(group)
    await session.commit()
    return result


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a group",
)
async def delete_group(
    group_id: str,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a group."""
    group = await group_repo.get_by_id(group_id)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Ensure account isolation (skip for superadmins)
    if current_user.account_id != SYSTEM_ACCOUNT_ID and group.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    await group_repo.delete(group)
    await session.commit()


@router.post(
    "/{group_id}/users",
    status_code=status.HTTP_201_CREATED,
    summary="Add user to group",
)
async def add_user_to_group(
    group_id: str,
    user_data: UserGroupUpdate,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Add a user to a group."""
    group = await group_repo.get_by_id(group_id)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Ensure account isolation (skip for superadmins)
    if current_user.account_id != SYSTEM_ACCOUNT_ID and group.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Verify user exists in account (TODO: better validation needed)
    
    # Check if already in group
    if await group_repo.is_user_in_group(group_id, user_data.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already in group",
        )
        
    await group_repo.add_user(group_id, user_data.user_id)
    await session.commit()
    
    return {"message": "User added to group"}


@router.delete(
    "/{group_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from group",
)
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    current_user: AuthenticatedUser,
    group_repo: GroupRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Remove a user from a group."""
    group = await group_repo.get_by_id(group_id)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    # Ensure account isolation (skip for superadmins)
    if current_user.account_id != SYSTEM_ACCOUNT_ID and group.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
        
    await group_repo.remove_user(group_id, user_id)
    await session.commit()
