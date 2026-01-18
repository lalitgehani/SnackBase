"""Authorization middleware for permission checking.

Provides functions to check permissions on collection CRUD operations,
apply field-level filtering, and enforce row-level security.
"""

import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.core.rules.sql_compiler import compile_to_sql
from snackbase.core.rules.lexer import Lexer
from snackbase.core.rules.parser import Parser
from snackbase.core.macros.expander import MacroExpander
from snackbase.infrastructure.api.dependencies import (
    SYSTEM_ACCOUNT_ID,
    AuthorizationContext,
    CurrentUser,
)
from snackbase.infrastructure.persistence.repositories import CollectionRuleRepository, RecordRepository
from snackbase.infrastructure.persistence.repositories.record_repository import RuleFilter

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
    request_data: dict[str, Any] | None = None,
) -> RuleFilter:
    """Check if user has permission for collection operation.

    Args:
        auth_context: Authorization context with user and role info.
        collection: Collection name.
        operation: Operation type (list, view, create, update, delete).
        session: Database session.
        record: Optional record data for rule evaluation context.

    Returns:
        RuleFilter object containing SQL fragment and allowed fields.

    Raises:
        HTTPException: 403 if permission denied or 404 if view/update/delete 
                      is on a record that doesn't pass the filter.
    """
    user = auth_context.user
    
    # 1. Superadmin bypass
    if user.account_id == SYSTEM_ACCOUNT_ID:
        logger.debug(
            "Superadmin bypass: permission check skipped",
            user_id=user.user_id,
            collection=collection,
            operation=operation,
        )
        return RuleFilter(sql="1=1", params={}, allowed_fields="*")

    # 2. Fetch collection rules
    rule_repo = CollectionRuleRepository(session)
    rules = await rule_repo.get_by_collection_name(collection)
    
    if not rules:
        logger.warning(
            "No rules found for collection - denying access by default",
            collection=collection,
            operation=operation,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied for {operation} on {collection} (no rules defined)",
        )

    # 3. Resolve rule and fields based on operation
    rule_expr = None
    allowed_fields = "*"
    
    if operation == "list":
        rule_expr = rules.list_rule
        allowed_fields = rules.list_fields
    elif operation == "view":
        rule_expr = rules.view_rule
        allowed_fields = rules.view_fields
    elif operation == "create":
        rule_expr = rules.create_rule
        allowed_fields = rules.create_fields
    elif operation == "update":
        rule_expr = rules.update_rule
        allowed_fields = rules.update_fields
    elif operation == "delete":
        rule_expr = rules.delete_rule
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operation: {operation}",
        )

    # Parse allowed_fields if it's a JSON string representative of an array
    if isinstance(allowed_fields, str) and allowed_fields != "*":
        try:
            import json
            allowed_fields = json.loads(allowed_fields)
        except json.JSONDecodeError:
            allowed_fields = "*"

    # 4. Handle locked state (null)
    if rule_expr is None:
        logger.warning(
            "Operation is locked (null rule)",
            collection=collection,
            operation=operation,
            user_id=user.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {operation} is locked for this collection",
        )

    # 5. Build auth context for evaluation/compilation
    auth_data = {
        "id": user.user_id,
        "email": user.email,
        "role": user.role,
        "account_id": user.account_id,
    }

    # 6. Expand macros
    expander = MacroExpander(session)
    try:
        rule_expr = await expander.expand(rule_expr)
    except Exception as e:
        logger.error("Macro expansion failed", error=str(e), rule=rule_expr)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error: macro expansion failed",
        )

    # 7. Operation-specific enforcement
    
    # For 'create', we should ideally validate against the DB
    # but for now we'll rely on the fact that any subsequent read would fail
    # or we can implement a simple SQL check in the future.
    if operation == "create":
        if rule_expr == "":
            return RuleFilter(sql="1=1", params={}, allowed_fields=allowed_fields)
            
        # Compile to SQL to validate syntax and get params
        try:
            sql, params = compile_to_sql(rule_expr, auth_data)
            
            # For 'create', we validate by running a dummy select with payload data
            # Use CTE to provide mock record values for the WHERE clause
            # Only include fields present in request_data
            if not request_data:
                request_data = {}
                
            cols = []
            cte_params = {}
            for k, v in request_data.items():
                param_name = f"payload_{k}"
                cols.append(f":{param_name} AS {k}")
                cte_params[param_name] = v
                
            # Also handle @request.data.* variables in the SQL
            for p_name in list(params.keys()):
                if p_name.startswith("data_"):
                    field = p_name[len("data_"):]
                    params[p_name] = request_data.get(field)
            
            if not cols:
                # If no data, just run the check directly (might only use @request.auth or constants)
                check_sql = f"SELECT 1 WHERE {sql}"
            else:
                check_sql = f"WITH payload AS (SELECT {', '.join(cols)}) SELECT 1 FROM payload WHERE {sql}"
            
            # Use same params for both CTE and original SQL
            all_params = {**params, **cte_params}
            
            from sqlalchemy import text
            res = await session.execute(text(check_sql), all_params)
            val = res.scalar()
            if not val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Record does not satisfy collection rules",
                )
                
            return RuleFilter(sql="1=1", params={}, allowed_fields=allowed_fields)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Rule validation failed for create", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Record does not satisfy collection rules or invalid rule expression",
            )

    # For other operations (list, view, update, delete), compile to SQL
    try:
        sql, params = compile_to_sql(rule_expr, auth_data)
        
        # If we have a record (view/update), we can also double check it here if desired,
        # but the repository layer will use the WHERE clause which is more consistent.
        
        return RuleFilter(sql=sql, params=params, allowed_fields=allowed_fields)
        
    except Exception as e:
        logger.error("Rule compilation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error: permission rule compilation failed",
        )
