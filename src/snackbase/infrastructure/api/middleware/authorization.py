"""Authorization middleware for permission checking.

Provides functions to check permissions on collection CRUD operations,
apply field-level filtering, and enforce row-level security.
"""

import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import PermissionResolver
from snackbase.infrastructure.api.dependencies import (
    SYSTEM_ACCOUNT_ID,
    AuthorizationContext,
    CurrentUser,
)

logger = get_logger(__name__)

# System fields that are always readable but never writable via API
SYSTEM_FIELDS = {"id", "account_id", "created_at", "updated_at", "created_by", "updated_by"}


def extract_operation_from_method(method: str) -> str:
    """Extract CRUD operation from HTTP method.
    
    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        
    Returns:
        Operation type (create, read, update, delete).
    """
    method = method.upper()
    if method == "POST":
        return "create"
    elif method == "GET":
        return "read"
    elif method in ("PUT", "PATCH"):
        return "update"
    elif method == "DELETE":
        return "delete"
    else:
        return "read"  # Default to read for unknown methods


def extract_collection_from_path(path: str) -> str | None:
    """Extract collection name from URL path.
    
    Matches patterns like:
    - /api/v1/{collection}
    - /api/v1/{collection}/{record_id}
    
    Args:
        path: URL path.
        
    Returns:
        Collection name if found, None otherwise.
    """
    # Pattern: /api/v1/{collection} or /api/v1/{collection}/{record_id}
    # Exclude specific routes like /auth, /permissions, /collections, /invitations, /macros
    excluded_routes = {
        "auth",
        "permissions",
        "collections",
        "invitations",
        "macros",
        "health",
        "ready",
        "live",
    }
    
    # Match /api/v1/{collection} or /api/v1/{collection}/{anything}
    pattern = r"^/api/v\d+/([^/]+)(?:/.*)?$"
    match = re.match(pattern, path)
    
    if match:
        collection = match.group(1)
        if collection not in excluded_routes:
            return collection
    
    return None


def validate_request_fields(
    data: dict[str, Any],
    allowed_fields: list[str] | str,
    operation: str,
) -> None:
    """Validate that request body only contains allowed fields.
    
    Checks that:
    1. All fields in the request are in the allowed fields list
    2. No system fields are present in the request (they cannot be written)
    
    Args:
        data: Request data dictionary.
        allowed_fields: List of allowed field names or "*" for all fields.
        operation: Operation type (create, update) for error messages.
        
    Raises:
        HTTPException: 422 if validation fails with details about unauthorized fields.
    """
    if allowed_fields == "*":
        # Wildcard allows all fields except system fields
        unauthorized_fields = set(data.keys()) & SYSTEM_FIELDS
        if unauthorized_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "error": "Field access denied",
                    "message": (
                        f"Cannot {operation} system fields via API: "
                        f"{', '.join(sorted(unauthorized_fields))}"
                    ),
                    "unauthorized_fields": sorted(unauthorized_fields),
                    "field_type": "system",
                },
            )
        return
    
    if isinstance(allowed_fields, str):
        # Should not happen, but handle gracefully
        return
    
    # Check for system fields in request
    system_fields_in_request = set(data.keys()) & SYSTEM_FIELDS
    if system_fields_in_request:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "Field access denied",
                "message": (
                    f"Cannot {operation} system fields via API: "
                    f"{', '.join(sorted(system_fields_in_request))}"
                ),
                "unauthorized_fields": sorted(system_fields_in_request),
                "field_type": "system",
            },
        )
    
    # Check for fields not in allowed list
    request_fields = set(data.keys())
    allowed_set = set(allowed_fields)
    unauthorized_fields = request_fields - allowed_set
    
    if unauthorized_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "Field access denied",
                "message": (
                    f"Permission denied to {operation} fields: "
                    f"{', '.join(sorted(unauthorized_fields))}"
                ),
                "unauthorized_fields": sorted(unauthorized_fields),
                "allowed_fields": sorted(allowed_fields),
                "field_type": "restricted",
            },
        )


def apply_field_filter(
    data: dict[str, Any],
    allowed_fields: list[str] | str,
    is_request: bool = False,
) -> dict[str, Any]:
    """Apply field-level filtering to data.
    
    Args:
        data: Data dictionary to filter.
        allowed_fields: List of allowed field names or "*" for all fields.
        is_request: If True, filtering for request body (excludes system fields).
                   If False, filtering for response (includes system fields).
        
    Returns:
        Filtered data dictionary.
    """
    if allowed_fields == "*":
        return data
    
    if isinstance(allowed_fields, str):
        # Should not happen, but handle gracefully
        return data
    
    # Filter to only allowed fields
    if is_request:
        # For requests: only allow the specified fields (no system fields)
        all_allowed = set(allowed_fields)
    else:
        # For responses: always include system fields
        all_allowed = set(allowed_fields) | SYSTEM_FIELDS
    
    return {k: v for k, v in data.items() if k in all_allowed}


async def check_collection_permission(
    auth_context: AuthorizationContext,
    collection: str,
    operation: str,
    session: AsyncSession,
    record: dict[str, Any] | None = None,
) -> tuple[bool, list[str] | str]:
    """Check if user has permission for collection operation.
    
    Args:
        auth_context: Authorization context with user and role info.
        collection: Collection name.
        operation: Operation type (create, read, update, delete).
        session: Database session.
        record: Optional record data for rule evaluation context.
        
    Returns:
        Tuple of (allowed: bool, fields: list[str] | "*").
        
    Raises:
        HTTPException: 403 if permission denied.
    """
    user = auth_context.user
    
    # Superadmin bypass
    if user.account_id == SYSTEM_ACCOUNT_ID:
        logger.debug(
            "Superadmin bypass: permission check skipped",
            user_id=user.user_id,
            collection=collection,
            operation=operation,
        )
        return (True, "*")
    
    # Check cache first
    cached_result = auth_context.permission_cache.get(
        user_id=user.user_id,
        collection=collection,
        operation=operation,
    )
    
    if cached_result is not None:
        logger.debug(
            "Permission check (cached)",
            user_id=user.user_id,
            collection=collection,
            operation=operation,
            allowed=cached_result.allowed,
        )
        
        if not cached_result.allowed:
            logger.warning(
                "Authorization denied (cached)",
                user_id=user.user_id,
                account_id=user.account_id,
                collection=collection,
                operation=operation,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for {operation} on {collection}",
            )
        
        return (cached_result.allowed, cached_result.fields)
    
    # Resolve permission
    resolver = PermissionResolver(session)
    
    # Build context for rule evaluation
    context = {
        "user": {
            "id": user.user_id,
            "email": user.email,
            "role": user.role,
            "account_id": user.account_id,
        },
        "account": {
            "id": user.account_id,
        },
    }
    
    if record is not None:
        context["record"] = record
    
    try:
        result = await resolver.resolve_permission(
            user_id=user.user_id,
            role_id=auth_context.role_id,
            collection=collection,
            operation=operation,
            context=context,
        )
        
        # Cache the result
        auth_context.permission_cache.set(
            user_id=user.user_id,
            collection=collection,
            operation=operation,
            value=result,
        )
        
        logger.debug(
            "Permission check completed",
            user_id=user.user_id,
            collection=collection,
            operation=operation,
            allowed=result.allowed,
            fields=result.fields if result.allowed else None,
        )
        
        if not result.allowed:
            logger.warning(
                "Authorization denied",
                user_id=user.user_id,
                account_id=user.account_id,
                collection=collection,
                operation=operation,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for {operation} on {collection}",
            )
        
        return (result.allowed, result.fields)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Permission check failed",
            user_id=user.user_id,
            collection=collection,
            operation=operation,
            error=str(e),
            exc_info=True,
        )
        # Deny by default on error
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission check failed",
        )
