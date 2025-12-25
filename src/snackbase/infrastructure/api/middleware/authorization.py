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


def apply_field_filter(
    data: dict[str, Any],
    allowed_fields: list[str] | str,
) -> dict[str, Any]:
    """Apply field-level filtering to data.
    
    Args:
        data: Data dictionary to filter.
        allowed_fields: List of allowed field names or "*" for all fields.
        
    Returns:
        Filtered data dictionary.
    """
    if allowed_fields == "*":
        return data
    
    if isinstance(allowed_fields, str):
        # Should not happen, but handle gracefully
        return data
    
    # Filter to only allowed fields
    # Always include system fields for responses
    system_fields = {"id", "account_id", "created_at", "updated_at", "created_by", "updated_by"}
    all_allowed = set(allowed_fields) | system_fields
    
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
