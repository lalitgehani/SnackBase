"""Accounts API routes.

Provides endpoints for account management (superadmin only).
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.account_service import AccountService
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import (
    AccountDetailResponse,
    AccountListItem,
    AccountListResponse,
    AccountUserResponse,
    AccountUsersResponse,
    CreateAccountRequest,
    UpdateAccountRequest,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories import UserRepository

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=AccountListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_accounts(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Column to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    search: str | None = Query(None, description="Search query"),
) -> AccountListResponse:
    """List all accounts with pagination, sorting, and search.

    Returns a paginated list of accounts with user counts.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    # Validate sort_by column
    valid_sort_columns = ["id", "slug", "name", "created_at"]
    if sort_by not in valid_sort_columns:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid sort_by column. Must be one of: {', '.join(valid_sort_columns)}",
        )

    # Get accounts with user counts
    accounts_with_counts, total = await account_service.list_accounts(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )

    # Build response items
    items = [
        AccountListItem(
            id=account.id,
            account_code=account.account_code,
            slug=account.slug,
            name=account.name,
            created_at=account.created_at,
            user_count=user_count,
            status="active",
        )
        for account, user_count in accounts_with_counts
    ]

    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AccountListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=AccountDetailResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Account not found"},
    },
)
async def get_account(
    account_id: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> AccountDetailResponse:
    """Get detailed account information.

    Returns account details including user count and collections used.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    try:
        account, user_count = await account_service.get_account_with_details(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # TODO: Get collections used by this account (requires collection-account relationship)
    collections_used: list[str] = []

    return AccountDetailResponse(
        id=account.id,
        account_code=account.account_code,
        slug=account.slug,
        name=account.name,
        created_at=account.created_at,
        updated_at=account.updated_at,
        user_count=user_count,
        collections_used=collections_used,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AccountDetailResponse,
    responses={
        403: {"description": "Superadmin access required"},
        422: {"description": "Validation error"},
    },
)
async def create_account(
    request: CreateAccountRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> AccountDetailResponse:
    """Create a new account.

    Creates a new account with auto-generated ID and optional slug.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    try:
        account = await account_service.create_account(
            name=request.name,
            slug=request.slug,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    # Get user count (should be 0 for new account)
    user_count = 0

    return AccountDetailResponse(
        id=account.id,
        account_code=account.account_code,
        slug=account.slug,
        name=account.name,
        created_at=account.created_at,
        updated_at=account.updated_at,
        user_count=user_count,
        collections_used=[],
    )


@router.put(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=AccountDetailResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Account not found"},
    },
)
async def update_account(
    account_id: str,
    request: UpdateAccountRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> AccountDetailResponse:
    """Update an account.

    Updates the account name. Slug and ID are immutable.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    try:
        account = await account_service.update_account(
            account_id=account_id,
            name=request.name,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Get user count
    account, user_count = await account_service.get_account_with_details(account_id)

    return AccountDetailResponse(
        id=account.id,
        account_code=account.account_code,
        slug=account.slug,
        name=account.name,
        created_at=account.created_at,
        updated_at=account.updated_at,
        user_count=user_count,
        collections_used=[],
    )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Account not found"},
        422: {"description": "Cannot delete system account"},
    },
)
async def delete_account(
    account_id: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an account.

    Deletes the account and all associated users and data (cascade).
    System account (nil UUID) cannot be deleted.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    try:
        await account_service.delete_account(account_id)
        await session.commit()
    except ValueError as e:
        if "system account" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{account_id}/users",
    status_code=status.HTTP_200_OK,
    response_model=AccountUsersResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Account not found"},
    },
)
async def get_account_users(
    account_id: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
) -> AccountUsersResponse:
    """Get users in an account.

    Returns a paginated list of users for the specified account.
    Only superadmins can access this endpoint.
    """
    account_service = AccountService(session)

    # Verify account exists
    try:
        await account_service.get_account_with_details(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Get users for this account
    user_repo = UserRepository(session)
    users, total = await user_repo.get_by_account_paginated(
        account_id=account_id,
        page=page,
        page_size=page_size,
    )

    # Build response items
    items = [
        AccountUserResponse(
            id=user.id,
            email=user.email,
            role=user.role.name if user.role else "unknown",
            is_active=user.is_active,
            created_at=user.created_at,
        )
        for user in users
    ]

    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AccountUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
