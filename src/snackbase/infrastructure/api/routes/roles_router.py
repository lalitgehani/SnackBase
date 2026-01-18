"""Roles API routes.

Provides endpoints for role management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas.role_schemas import (
    CreateRoleRequest,
    RoleListItem,
    RoleListResponse,
    RoleResponse,
    UpdateRoleRequest,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import RoleModel
from snackbase.infrastructure.persistence.repositories import RoleRepository

logger = get_logger(__name__)

router = APIRouter()

# Default roles that cannot be deleted
DEFAULT_ROLES = {"admin", "user"}


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=RoleListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_roles(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RoleListResponse:
    """List all roles.

    Only superadmins can access this endpoint.

    Args:
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        List of all roles.
    """
    role_repo = RoleRepository(session)
    roles = await role_repo.list_all()

    items = []
    for role in roles:
        items.append(
            RoleListItem(
                id=role.id,
                name=role.name,
                description=role.description,
            )
        )

    logger.debug(
        "Roles listed",
        count=len(items),
        requested_by=current_user.user_id,
    )

    return RoleListResponse(items=items, total=len(items))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RoleResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Superadmin access required"},
        409: {"description": "Role name already exists"},
    },
)
async def create_role(
    role_request: CreateRoleRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Create a new role.

    Creates a role with the specified name and description.
    Only superadmins can create roles.

    Args:
        role_request: Role creation request.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Created role.
    """
    role_repo = RoleRepository(session)

    # Check if role name already exists
    existing_role = await role_repo.get_by_name(role_request.name)
    if existing_role:
        logger.info(
            "Role creation failed: name already exists",
            role_name=role_request.name,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role with name '{role_request.name}' already exists",
        )

    # Create role
    role = RoleModel(
        name=role_request.name,
        description=role_request.description,
    )
    await role_repo.create(role)
    await session.commit()
    await session.refresh(role)

    logger.info(
        "Role created successfully",
        role_id=role.id,
        role_name=role.name,
        created_by=current_user.user_id,
    )

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
    )


@router.get(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=RoleResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
    },
)
async def get_role(
    role_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Get a role by ID.

    Only superadmins can view role details.

    Args:
        role_id: Role ID.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Role details.
    """
    role_repo = RoleRepository(session)
    role = await role_repo.get_by_id(role_id)

    if role is None:
        logger.info(
            "Role not found",
            role_id=role_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
    )


@router.put(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=RoleResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
        409: {"description": "Role name already exists"},
    },
)
async def update_role(
    role_id: int,
    role_request: UpdateRoleRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Update a role.

    Updates the role name and description.
    Only superadmins can update roles.

    Args:
        role_id: Role ID.
        role_request: Role update request.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Updated role.
    """
    role_repo = RoleRepository(session)

    # Check if role exists
    role = await role_repo.get_by_id(role_id)
    if role is None:
        logger.info(
            "Role update failed: role not found",
            role_id=role_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    # Check if new name conflicts with existing role
    if role_request.name != role.name:
        existing_role = await role_repo.get_by_name(role_request.name)
        if existing_role:
            logger.info(
                "Role update failed: name already exists",
                role_name=role_request.name,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role with name '{role_request.name}' already exists",
            )

    # Update role
    updated_role = await role_repo.update(
        role_id=role_id,
        name=role_request.name,
        description=role_request.description,
    )
    await session.commit()
    await session.refresh(updated_role)

    logger.info(
        "Role updated successfully",
        role_id=role_id,
        updated_by=current_user.user_id,
    )

    return RoleResponse(
        id=updated_role.id,
        name=updated_role.name,
        description=updated_role.description,
    )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
        422: {"description": "Cannot delete default role"},
    },
)
async def delete_role(
    role_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a role.

    Deletes the role.
    Default roles (admin, user) cannot be deleted.
    Only superadmins can delete roles.

    Args:
        role_id: Role ID.
        current_user: Authenticated superadmin user.
        session: Database session.
    """
    role_repo = RoleRepository(session)

    # Check if role exists
    role = await role_repo.get_by_id(role_id)
    if role is None:
        logger.info(
            "Role deletion failed: role not found",
            role_id=role_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    # Prevent deletion of default roles
    if role.name in DEFAULT_ROLES:
        logger.info(
            "Role deletion failed: cannot delete default role",
            role_id=role_id,
            role_name=role.name,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Cannot delete default role '{role.name}'",
        )

    # Delete role
    deleted = await role_repo.delete(role_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    await session.commit()

    logger.info(
        "Role deleted successfully",
        role_id=role_id,
        deleted_by=current_user.user_id,
    )
