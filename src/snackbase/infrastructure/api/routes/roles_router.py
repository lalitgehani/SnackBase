"""Roles API routes.

Provides endpoints for role management and permission configuration.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.core.macros.engine import MacroExecutionEngine
from snackbase.core.rules.evaluator import Evaluator
from snackbase.core.rules.lexer import Lexer
from snackbase.core.rules.parser import Parser
from snackbase.infrastructure.api.dependencies import SuperadminUser, get_permission_cache
from snackbase.infrastructure.api.schemas import (
    BulkPermissionUpdateRequest,
    BulkPermissionUpdateResponse,
    CollectionPermission,
    CreateRoleRequest,
    RoleListItem,
    RoleListResponse,
    RolePermissionsResponse,
    RoleResponse,
    TestRuleRequest,
    TestRuleResponse,
    UpdateRoleRequest,
    ValidateRuleRequest,
    ValidateRuleResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import PermissionModel, RoleModel
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    PermissionRepository,
    RoleRepository,
)

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
    """List all roles with collections count.

    Only superadmins can access this endpoint.

    Args:
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        List of all roles with collections count.
    """
    role_repo = RoleRepository(session)
    roles = await role_repo.list_all()

    items = []
    for role in roles:
        collections_count = await role_repo.get_permissions_count(role.id)
        items.append(
            RoleListItem(
                id=role.id,
                name=role.name,
                description=role.description,
                collections_count=collections_count,
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
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a role.

    Deletes the role and all associated permissions.
    Default roles (admin, user) cannot be deleted.
    Only superadmins can delete roles.

    Args:
        role_id: Role ID.
        current_user: Authenticated superadmin user.
        request: FastAPI request object.
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

    # Delete role (permissions will be cascade deleted)
    deleted = await role_repo.delete(role_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    await session.commit()

    # Invalidate permission cache
    permission_cache = get_permission_cache(request)
    permission_cache.invalidate_all()

    logger.info(
        "Role deleted successfully",
        role_id=role_id,
        deleted_by=current_user.user_id,
    )


@router.get(
    "/{role_id}/permissions",
    status_code=status.HTTP_200_OK,
    response_model=RolePermissionsResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
    },
)
async def get_role_permissions(
    role_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RolePermissionsResponse:
    """Get all permissions for a role organized by collection.

    Only superadmins can view role permissions.

    Args:
        role_id: Role ID.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Role permissions organized by collection.
    """
    role_repo = RoleRepository(session)
    permission_repo = PermissionRepository(session)

    # Check if role exists
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

    # Get all permissions for this role
    permissions = await permission_repo.get_by_role_id(role_id)

    # Organize by collection
    collection_permissions: dict[str, CollectionPermission] = {}
    for perm in permissions:
        collection = perm.collection
        if collection not in collection_permissions:
            collection_permissions[collection] = CollectionPermission(
                collection=collection,
                permission_id=perm.id,
            )

        # Parse rules
        rules_dict = json.loads(perm.rules)
        for op in ["create", "read", "update", "delete"]:
            if op in rules_dict:
                setattr(collection_permissions[collection], op, rules_dict[op])

    return RolePermissionsResponse(
        role_id=role.id,
        role_name=role.name,
        permissions=list(collection_permissions.values()),
    )


@router.get(
    "/{role_id}/permissions/matrix",
    status_code=status.HTTP_200_OK,
    response_model=RolePermissionsResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
    },
)
async def get_permissions_matrix(
    role_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> RolePermissionsResponse:
    """Get permissions in matrix format for a role.

    Returns permissions for ALL collections (even those without permissions set),
    making it suitable for displaying in a permission matrix UI.

    Only superadmins can access this endpoint.

    Args:
        role_id: Role ID.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Role permissions in matrix format with all collections.
    """
    role_repo = RoleRepository(session)
    permission_repo = PermissionRepository(session)
    collection_repo = CollectionRepository(session)

    # Check if role exists
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

    # Get all collections
    all_collections = await collection_repo.list_all()

    # Get all permissions for this role
    permissions = await permission_repo.get_by_role_id(role_id)

    # Create a map of collection -> permission
    permission_map: dict[str, PermissionModel] = {}
    for perm in permissions:
        permission_map[perm.collection] = perm

    # Build matrix with all collections
    collection_permissions: list[CollectionPermission] = []
    for collection in all_collections:
        collection_name = collection.name
        perm = permission_map.get(collection_name)

        if perm:
            # Parse existing rules
            rules_dict = json.loads(perm.rules)
            collection_permissions.append(
                CollectionPermission(
                    collection=collection_name,
                    permission_id=perm.id,
                    create=rules_dict.get("create"),
                    read=rules_dict.get("read"),
                    update=rules_dict.get("update"),
                    delete=rules_dict.get("delete"),
                )
            )
        else:
            # No permission set for this collection
            collection_permissions.append(
                CollectionPermission(
                    collection=collection_name,
                    permission_id=None,
                    create=None,
                    read=None,
                    update=None,
                    delete=None,
                )
            )

    logger.debug(
        "Permission matrix retrieved",
        role_id=role_id,
        collections_count=len(collection_permissions),
        requested_by=current_user.user_id,
    )

    return RolePermissionsResponse(
        role_id=role.id,
        role_name=role.name,
        permissions=collection_permissions,
    )


@router.put(
    "/{role_id}/permissions/bulk",
    status_code=status.HTTP_200_OK,
    response_model=BulkPermissionUpdateResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Superadmin access required"},
        404: {"description": "Role not found"},
    },
)
async def bulk_update_permissions(
    role_id: int,
    bulk_request: BulkPermissionUpdateRequest,
    current_user: SuperadminUser,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> BulkPermissionUpdateResponse:
    """Bulk update permissions for a role.

    Updates multiple collection-operation permissions in a single request.
    Only superadmins can update permissions.

    Args:
        role_id: Role ID.
        bulk_request: Bulk update request with list of updates.
        current_user: Authenticated superadmin user.
        request: FastAPI request object.
        session: Database session.

    Returns:
        Bulk update response with success/failure counts.
    """
    role_repo = RoleRepository(session)
    permission_repo = PermissionRepository(session)
    collection_repo = CollectionRepository(session)

    # Check if role exists
    role = await role_repo.get_by_id(role_id)
    if role is None:
        logger.info(
            "Bulk update failed: role not found",
            role_id=role_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    success_count = 0
    failure_count = 0
    errors: list[str] = []

    # Process each update
    for update in bulk_request.updates:
        try:
            # Validate collection exists
            collection = await collection_repo.get_by_name(update.collection)
            if not collection:
                errors.append(f"Collection '{update.collection}' not found")
                failure_count += 1
                continue

            # Validate rule syntax
            try:
                lexer = Lexer(update.rule)
                parser = Parser(lexer)
                parser.parse()
            except Exception as e:
                errors.append(
                    f"Invalid rule for {update.collection}/{update.operation}: {str(e)}"
                )
                failure_count += 1
                continue

            # Find or create permission for this collection
            existing_perms = await permission_repo.get_by_role_id(role_id)
            existing_perm = next(
                (p for p in existing_perms if p.collection == update.collection), None
            )

            if existing_perm:
                # Update existing permission
                rules_dict = json.loads(existing_perm.rules)
                rules_dict[update.operation] = {
                    "rule": update.rule,
                    "fields": update.fields,
                }
                existing_perm.rules = json.dumps(rules_dict)
            else:
                # Create new permission
                rules_dict = {
                    update.operation: {
                        "rule": update.rule,
                        "fields": update.fields,
                    }
                }
                new_perm = PermissionModel(
                    role_id=role_id,
                    collection=update.collection,
                    rules=json.dumps(rules_dict),
                )
                await permission_repo.create(new_perm)

            success_count += 1

        except Exception as e:
            errors.append(
                f"Error updating {update.collection}/{update.operation}: {str(e)}"
            )
            failure_count += 1

    # Commit all changes
    await session.commit()

    # Invalidate permission cache
    permission_cache = get_permission_cache(request)
    permission_cache.invalidate_all()

    logger.info(
        "Bulk permission update completed",
        role_id=role_id,
        success_count=success_count,
        failure_count=failure_count,
        updated_by=current_user.user_id,
    )

    return BulkPermissionUpdateResponse(
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
    )


@router.post(
    "/validate-rule",
    status_code=status.HTTP_200_OK,
    response_model=ValidateRuleResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def validate_rule(
    validate_request: ValidateRuleRequest,
    current_user: SuperadminUser,
) -> ValidateRuleResponse:
    """Validate a permission rule expression.

    Checks if the rule syntax is valid without executing it.
    Only superadmins can validate rules.

    Args:
        validate_request: Rule validation request.
        current_user: Authenticated superadmin user.

    Returns:
        Validation result with position information if error.
    """
    try:
        # Try to parse the rule
        lexer = Lexer(validate_request.rule)
        parser = Parser(lexer)
        parser.parse()

        logger.debug(
            "Rule validation successful",
            rule=validate_request.rule,
            validated_by=current_user.user_id,
        )

        return ValidateRuleResponse(valid=True)
    except Exception as e:
        error_str = str(e)
        position = None

        # Try to extract position from error message if available
        # Common format: "Error at line X, column Y: ..."
        try:
            if "line" in error_str.lower() and "column" in error_str.lower():
                import re

                match = re.search(r"line\s+(\d+).*column\s+(\d+)", error_str, re.IGNORECASE)
                if match:
                    position = {"line": int(match.group(1)), "column": int(match.group(2))}
        except Exception:
            pass  # Position extraction failed, continue without it

        logger.debug(
            "Rule validation failed",
            rule=validate_request.rule,
            error=error_str,
            position=position,
        )
        return ValidateRuleResponse(valid=False, error=error_str, position=position)


@router.post(
    "/test-rule",
    status_code=status.HTTP_200_OK,
    response_model=TestRuleResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def test_rule(
    test_request: TestRuleRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> TestRuleResponse:
    """Test a permission rule with sample data.

    Evaluates the rule with the provided context to see if access would be granted.
    Only superadmins can test rules.

    Args:
        test_request: Rule test request.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Test result.
    """
    try:
        # Parse the rule
        lexer = Lexer(test_request.rule)
        parser = Parser(lexer)
        ast = parser.parse()

        # Evaluate with provided context
        macro_engine = MacroExecutionEngine(session)
        evaluator = Evaluator(test_request.context, macro_engine)
        result = await evaluator.evaluate(ast)

        allowed = bool(result)

        logger.debug(
            "Rule test successful",
            rule=test_request.rule,
            allowed=allowed,
            tested_by=current_user.user_id,
        )

        return TestRuleResponse(
            allowed=allowed,
            evaluation_details=f"Rule evaluated to: {result}",
        )
    except Exception as e:
        logger.debug(
            "Rule test failed",
            rule=test_request.rule,
            error=str(e),
        )
        return TestRuleResponse(
            allowed=False,
            error=str(e),
            evaluation_details="Rule evaluation failed",
        )
