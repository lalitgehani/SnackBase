"""Permissions API routes.

Provides endpoints for managing role-based permissions.
"""

import json

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser, get_permission_cache
from snackbase.infrastructure.api.schemas import (
    CreatePermissionRequest,
    OperationRuleSchema,
    PermissionListResponse,
    PermissionResponse,
    PermissionRulesSchema,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import PermissionModel
from snackbase.infrastructure.persistence.repositories import (
    PermissionRepository,
    RoleRepository,
)

logger = get_logger(__name__)

router = APIRouter()


def _parse_rules_from_json(rules_json: str) -> PermissionRulesSchema:
    """Parse rules JSON string into PermissionRulesSchema."""
    rules_dict = json.loads(rules_json)
    return PermissionRulesSchema(
        create=OperationRuleSchema(**rules_dict["create"])
        if rules_dict.get("create")
        else None,
        read=OperationRuleSchema(**rules_dict["read"])
        if rules_dict.get("read")
        else None,
        update=OperationRuleSchema(**rules_dict["update"])
        if rules_dict.get("update")
        else None,
        delete=OperationRuleSchema(**rules_dict["delete"])
        if rules_dict.get("delete")
        else None,
    )


def _permission_to_response(permission: PermissionModel) -> PermissionResponse:
    """Convert PermissionModel to PermissionResponse."""
    return PermissionResponse(
        id=permission.id,
        role_id=permission.role_id,
        collection=permission.collection,
        rules=_parse_rules_from_json(permission.rules),
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PermissionResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
    },
)
async def create_permission(
    permission_request: CreatePermissionRequest,
    current_user: SuperadminUser,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PermissionResponse | JSONResponse:
    """Create a new permission.

    Creates a permission linking a role to a collection with CRUD rules.
    Only superadmins can create permissions.

    Args:
        request: Permission creation request.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Created permission.
    """
    # Verify role exists
    role_repo = RoleRepository(session)
    role = await role_repo.get_by_id(permission_request.role_id)
    if role is None:
        logger.info(
            "Permission creation failed: role not found",
            role_id=permission_request.role_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Role with ID {permission_request.role_id} not found",
            },
        )

    # Convert rules to JSON
    rules_dict = {}
    if permission_request.rules.create:
        rules_dict["create"] = {
            "rule": permission_request.rules.create.rule,
            "fields": permission_request.rules.create.fields,
        }
    if permission_request.rules.read:
        rules_dict["read"] = {
            "rule": permission_request.rules.read.rule,
            "fields": permission_request.rules.read.fields,
        }
    if permission_request.rules.update:
        rules_dict["update"] = {
            "rule": permission_request.rules.update.rule,
            "fields": permission_request.rules.update.fields,
        }
    if permission_request.rules.delete:
        rules_dict["delete"] = {
            "rule": permission_request.rules.delete.rule,
            "fields": permission_request.rules.delete.fields,
        }

    # Create permission
    permission_repo = PermissionRepository(session)
    permission = PermissionModel(
        role_id=permission_request.role_id,
        collection=permission_request.collection,
        rules=json.dumps(rules_dict),
    )
    await permission_repo.create(permission)
    await session.commit()
    await session.refresh(permission)

    # Invalidate permission cache for this collection
    permission_cache = get_permission_cache(request)
    permission_cache.invalidate_collection(permission.collection)
    
    logger.info(
        "Permission created successfully",
        permission_id=permission.id,
        role_id=permission.role_id,
        collection=permission.collection,
        created_by=current_user.user_id,
    )

    return _permission_to_response(permission)


@router.get(
    "",
    response_model=PermissionListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_permissions(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> PermissionListResponse:
    """List all permissions.

    Only superadmins can list permissions.

    Args:
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        List of all permissions.
    """
    permission_repo = PermissionRepository(session)
    permissions = await permission_repo.list_all()

    items = [_permission_to_response(p) for p in permissions]

    logger.debug(
        "Permissions listed",
        count=len(items),
        requested_by=current_user.user_id,
    )

    return PermissionListResponse(items=items, total=len(items))


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Permission not found"},
    },
)
async def get_permission(
    permission_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> PermissionResponse | JSONResponse:
    """Get a permission by ID.

    Only superadmins can view permission details.

    Args:
        permission_id: Permission ID.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Permission details.
    """
    permission_repo = PermissionRepository(session)
    permission = await permission_repo.get_by_id(permission_id)

    if permission is None:
        logger.info(
            "Permission not found",
            permission_id=permission_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Permission with ID {permission_id} not found",
            },
        )

    return _permission_to_response(permission)


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Permission not found"},
    },
)
async def delete_permission(
    permission_id: int,
    current_user: SuperadminUser,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a permission.

    Only superadmins can delete permissions.

    Args:
        permission_id: Permission ID.
        current_user: Authenticated superadmin user.
        request: FastAPI request object.
        session: Database session.
    """
    from fastapi import HTTPException

    permission_repo = PermissionRepository(session)
    
    # Get permission before deleting to invalidate cache
    permission = await permission_repo.get_by_id(permission_id)
    
    deleted = await permission_repo.delete(permission_id)

    if not deleted:
        logger.info(
            "Permission not found for deletion",
            permission_id=permission_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission with ID {permission_id} not found",
        )

    await session.commit()
    
    # Invalidate permission cache for this collection
    if permission:
        permission_cache = get_permission_cache(request)
        permission_cache.invalidate_collection(permission.collection)

    logger.info(
        "Permission deleted",
        permission_id=permission_id,
        deleted_by=current_user.user_id,
    )

