"""Records API routes.

Provides dynamic endpoints for CRUD operations on collection records.
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.cursor import CursorError, decode_cursor
from snackbase.core.logging import get_logger
from snackbase.core.rules import (
    AggregationParseError,
    FilterCompilationError,
    RuleSyntaxError,
    compile_filter_to_sql,
    parse_agg_functions,
    parse_having,
    validate_filter_expression,
    validate_group_by,
)
from snackbase.infrastructure.persistence.repositories.record_repository import (
    _build_computed_select_parts,
)
from snackbase.domain.services import FieldType, PIIMaskingService, RecordValidator
from snackbase.infrastructure.api.dependencies import (
    ANONYMOUS_USER_ID,
    AuthenticatedUser,
    AuthorizationContext,
    OptionalAuthContext,
    OptionalUser,
)
from snackbase.infrastructure.api.middleware import (
    RuleFilter,
    apply_field_filter,
    check_collection_permission,
    validate_request_fields,
)
from snackbase.infrastructure.api.schemas import (
    AggregationResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchDeleteRequest,
    BatchDeleteResponse,
    BatchUpdateRequest,
    BatchUpdateResponse,
    BatchValidationError,
    CursorListResponse,
    RecordListResponse,
    RecordResponse,
    RecordValidationErrorDetail,
    RecordValidationErrorResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    RecordRepository,
)

logger = get_logger(__name__)

router = APIRouter()


def _mask_record_pii(
    record: dict[str, Any],
    schema: list[dict],
    user_groups: list[str],
    account_id: str | None = None,
) -> dict[str, Any]:
    """Mask PII fields in a record based on user groups.

    Args:
        record: The record data to mask.
        schema: The collection schema with PII field definitions.
        user_groups: List of group names the user belongs to.
        account_id: Optional account ID for superadmin PII bypass.

    Returns:
        Record with PII fields masked if user doesn't have pii_access group.
    """
    # Check if user has pii_access group or is superadmin
    if not PIIMaskingService.should_mask_for_user(user_groups, account_id):
        # User has pii_access or is superadmin, return unmasked data
        return record

    # User doesn't have pii_access, mask PII fields
    masked_record = record.copy()

    for field in schema:
        field_name = field.get("name")
        is_pii = field.get("pii", False)
        mask_type = field.get("mask_type")

        if is_pii and field_name in masked_record and masked_record[field_name] is not None:
            # Determine mask type (use default if not specified)
            if not mask_type:
                # Default to 'full' masking if no mask_type specified
                mask_type = "full"

            # Apply masking
            masked_record[field_name] = PIIMaskingService.mask_value(
                masked_record[field_name],
                mask_type,
            )

    return masked_record


def _parse_expand_param(
    expand: str, schema: list[dict]
) -> tuple[list[list[str]], str | None]:
    """Parse and validate the ?expand= query parameter.

    Args:
        expand: Comma-separated expand paths, e.g. "company,team.industry"
        schema: The collection schema to validate reference fields.

    Returns:
        Tuple of (parsed paths, invalid_field_name). If invalid_field_name is not None,
        it means that field is not a reference type and should return a 400 error.
    """
    schema_lookup = {f["name"]: f for f in schema}
    paths: list[list[str]] = []
    for raw in expand.split(","):
        raw = raw.strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split(".") if p.strip()]
        if not parts:
            continue
        root = parts[0]
        field_def = schema_lookup.get(root)
        if not field_def or field_def.get("type") != "reference":
            return [], root
        paths.append(parts)
    return paths, None


async def _resolve_account_id(
    current_user: AuthenticatedUser | None,
    request: Request,
    session: AsyncSession,
) -> str:
    """Resolve account_id from JWT (authenticated) or X-Account-ID header (anonymous).

    Args:
        current_user: The authenticated user, or None for anonymous.
        request: The incoming request (used to read X-Account-ID header).
        session: Database session (used to validate the account from header).

    Returns:
        The account_id string to scope the request to.

    Raises:
        HTTPException: 400 if anonymous and X-Account-ID header is missing.
        HTTPException: 404 if the account from the header doesn't exist.
    """
    if current_user is not None:
        return current_user.account_id

    header_val = request.headers.get("X-Account-ID")
    if not header_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Account-ID header is required for unauthenticated requests",
        )

    from snackbase.infrastructure.persistence.repositories import AccountRepository

    account_repo = AccountRepository(session)
    account = await account_repo.get_by_slug_or_code(header_val)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{header_val}' not found",
        )
    return str(account.id)


async def _expand_records(
    records: list[dict[str, Any]],
    expand_paths: list[list[str]],
    schema: list[dict[str, Any]],
    account_id: str | None,
    collection_repo: CollectionRepository,
    record_repo: RecordRepository,
    depth: int,
    max_depth: int,
) -> list[dict[str, Any]]:
    """Recursively expand reference fields in records using batch loading.

    Args:
        records: List of record dicts to expand.
        expand_paths: List of field path lists, e.g. [["company", "industry"], ["team"]].
        schema: Schema of the current collection.
        account_id: Account ID for scoping (None for superadmin).
        collection_repo: CollectionRepository instance.
        record_repo: RecordRepository instance.
        depth: Current recursion depth.
        max_depth: Maximum allowed depth.

    Returns:
        Records with reference fields replaced by full record objects.
    """
    if depth >= max_depth or not expand_paths or not records:
        return records

    # Group sub-paths by root field name
    root_groups: dict[str, list[list[str]]] = {}
    for path in expand_paths:
        if path:
            root = path[0]
            if root not in root_groups:
                root_groups[root] = []
            if len(path) > 1:
                root_groups[root].append(path[1:])

    schema_lookup = {f["name"]: f for f in schema}

    for field_name, sub_paths in root_groups.items():
        field_def = schema_lookup.get(field_name)
        if not field_def or field_def.get("type") != "reference":
            continue
        target_collection = field_def.get("collection")
        if not target_collection:
            continue

        # Collect unique non-null reference IDs
        ids = {
            r[field_name]
            for r in records
            if r.get(field_name) and isinstance(r[field_name], str)
        }
        if not ids:
            continue

        # Fetch target collection schema
        target_model = await collection_repo.get_by_name(target_collection)
        if not target_model:
            for r in records:
                if r.get(field_name):
                    r[field_name] = None
            continue
        try:
            target_schema = json.loads(target_model.schema)
        except json.JSONDecodeError:
            continue

        # Batch fetch all referenced records
        fetched = await record_repo.get_by_ids(
            collection_name=target_collection,
            ids=list(ids),
            account_id=account_id,
            schema=target_schema,
        )

        # Recurse for nested expansion paths
        if sub_paths and depth + 1 < max_depth and fetched:
            expanded = await _expand_records(
                records=list(fetched.values()),
                expand_paths=sub_paths,
                schema=target_schema,
                account_id=account_id,
                collection_repo=collection_repo,
                record_repo=record_repo,
                depth=depth + 1,
                max_depth=max_depth,
            )
            fetched = {r["id"]: r for r in expanded}

        # Replace ID with full object (None if deleted or cross-account)
        for record in records:
            val = record.get(field_name)
            if val and isinstance(val, str):
                record[field_name] = fetched.get(val)

    return records


@router.post(
    "/{collection}",
    status_code=status.HTTP_201_CREATED,
    response_model=RecordResponse,
    responses={
        400: {"model": RecordValidationErrorResponse, "description": "Validation error"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Collection not found"},
    },
)
async def create_record(
    collection: str,
    request: Request,
    data: dict[str, Any],
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Create a new record in a collection.

    Validates the request data against the collection schema, auto-generates
    a record ID, and sets system fields (account_id, created_at, created_by).

    Args:
        collection: The collection name (from URL path).
        data: The record data (request body). May include 'account_id' for superadmins.
        current_user: The authenticated user, or None for anonymous.
        auth_context: Authorization context for permission checking.
        session: Database session.

    Returns:
        The created record with all fields including system fields.
    """
    # 0. Determine target account_id
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

    target_account_id = await _resolve_account_id(current_user, request, session)
    if current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID and "account_id" in data:
        target_account_id = data.pop("account_id")

    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        logger.info(
            "Record creation failed: collection not found",
            collection=collection,
            user_id=current_user.user_id if current_user else None,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Collection '{collection}' not found",
            },
        )

    # 1.5 Parse collection schema
    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse collection schema",
            collection=collection,
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to parse collection schema",
            },
        )

    # 1.6 Preliminary validation for defaults (needed for rule evaluation)
    processed_temp, _ = RecordValidator.validate_and_apply_defaults(data, schema)

    # 2. Check create permission (now includes rule evaluation)
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="create",
        session=session,
        record=processed_temp, # Pass processed data for rule evaluation (@request.data.*)
        request_data=data,
    )
    allowed_fields = rule_result.allowed_fields

    # Validate request fields (reject if contains unauthorized fields)
    validate_request_fields(data, allowed_fields, "create")

    # Filter request body to allowed fields only
    if allowed_fields != "*":
        data = apply_field_filter(data, allowed_fields, is_request=True)

    # 4. Validate reference fields (check if referenced records exist)
    record_repo = RecordRepository(session)
    reference_errors = []
    for field in schema:
        field_name = field["name"]
        field_type = field.get("type", "text").lower()

        if field_type == FieldType.REFERENCE.value and field_name in data:
            ref_value = data[field_name]
            if ref_value is not None:
                target_collection = field.get("collection", "")
                exists = await record_repo.check_reference_exists(
                    target_collection,
                    ref_value,
                    target_account_id,
                )
                if not exists:
                    reference_errors.append({
                        "field": field_name,
                        "message": f"Referenced record '{ref_value}' not found in collection '{target_collection}'",
                        "code": "invalid_reference",
                    })

    # 5. Validate record data against schema
    processed_data, validation_errors = RecordValidator.validate_and_apply_defaults(
        data, schema
    )

    # Combine validation errors
    all_errors = [
        RecordValidationErrorDetail(
            field=e.field,
            message=e.message,
            code=e.code,
        )
        for e in validation_errors
    ] + [
        RecordValidationErrorDetail(**e) for e in reference_errors
    ]

    if all_errors:
        logger.info(
            "Record creation failed: validation errors",
            collection=collection,
            error_count=len(all_errors),
            user_id=current_user.user_id if current_user else None,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=RecordValidationErrorResponse(
                error="Validation error",
                details=all_errors,
            ).model_dump(),
        )

    # 6. Generate record ID
    record_id = str(uuid.uuid4())

    # 7. Insert record
    try:
        created_record = await record_repo.insert_record(
            collection_name=collection,
            record_id=record_id,
            account_id=target_account_id,
            created_by=current_user.user_id if current_user else ANONYMOUS_USER_ID,
            data=processed_data,
            schema=schema,
        )
        await session.commit()
    except Exception as e:
        logger.error(
            "Record creation failed: database error",
            collection=collection,
            record_id=record_id,
            error=str(e),
        )
        # Check for foreign key constraint errors
        error_msg = str(e).lower()
        if "foreign key" in error_msg or "constraint" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": "Foreign key constraint violation - referenced record may not exist",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to create record",
            },
        )

    logger.info(
        "Record created successfully",
        collection=collection,
        record_id=record_id,
        account_id=target_account_id,
        created_by=current_user.user_id if current_user else None,
    )

    # 7.5 Broadcast create event
    try:
        broadcaster = request.app.state.event_broadcaster
        # Use full record for creation broadcast
        await broadcaster.publish_event(
            account_id=target_account_id,
            collection=collection,
            operation="create",
            data=created_record
        )
    except Exception as e:
        logger.error("Failed to broadcast create event", error=str(e))

    # 8. Apply field filter to response
    if allowed_fields != "*":
        created_record = apply_field_filter(created_record, allowed_fields)

    # 9. Apply PII masking to response
    created_record = _mask_record_pii(
        created_record, schema,
        current_user.groups if current_user else [],
        current_user.account_id if current_user else None,
    )

    return RecordResponse.from_record(created_record)


@router.get(
    "/{collection}",
    response_model=RecordListResponse | CursorListResponse,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Collection not found"},
    },
)
async def list_records(
    collection: str,
    request: Request,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("-created_at"),
    fields: str | None = Query(None),
    filter_expr: str | None = Query(None, alias="filter"),
    expand: str | None = Query(None),
    cursor: str | None = Query(None),
    cursor_before: str | None = Query(None),
    include_count: bool = Query(False),
    session: AsyncSession = Depends(get_db_session),
) -> RecordListResponse | CursorListResponse | JSONResponse:
    """List records in a collection.

    Supports pagination, sorting, and filtering.
    """
    # 0. Check read/list permission
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="list",
        session=session,
    )
    allowed_fields = rule_result.allowed_fields

    # 1. Look up collection
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Collection '{collection}' not found",
            },
        )

    # 2. Parse schema
    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Invalid collection schema"},
        )

    # 3. Parse sort parameter
    descending = True
    sort_by = "created_at"

    if sort.startswith("-"):
        descending = True
        sort_by = sort[1:]
    elif sort.startswith("+"):
        descending = False
        sort_by = sort[1:]
    else:
        # Default behavior or handle bare field name
        sort_by = sort

    # 4. Reject old-style query param filters and parse the new filter expression
    reserved_params = {"skip", "limit", "sort", "fields", "filter", "expand", "cursor", "cursor_before", "include_count"}
    legacy_params = [k for k in request.query_params if k not in reserved_params]
    if legacy_params:
        example_field = legacy_params[0]
        example_value = request.query_params[example_field]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Unsupported query parameter",
                "message": (
                    f"Direct query parameter filtering (e.g., ?{example_field}={example_value}) "
                    "is no longer supported. "
                    f'Use the \'filter\' parameter instead: ?filter={example_field} = "{example_value}"'
                ),
            },
        )

    # 4b. Determine pagination mode
    is_cursor_mode = cursor is not None or cursor_before is not None
    if is_cursor_mode and (skip != 0):
        # In cursor mode, skip is ignored
        skip = 0

    # 4c. Validate cursor parameters
    if cursor and cursor_before:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid pagination parameters",
                "message": "Cannot specify both 'cursor' and 'cursor_before'",
            },
        )

    cursor_sort_value = None
    cursor_record_id = None
    is_backward = False

    if cursor:
        try:
            cursor_sort_value, cursor_record_id = decode_cursor(cursor)
        except CursorError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid cursor",
                    "message": str(e),
                },
            )
    elif cursor_before:
        try:
            cursor_sort_value, cursor_record_id = decode_cursor(cursor_before)
            is_backward = True
        except CursorError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid cursor_before",
                    "message": str(e),
                },
            )

    # Normalize filter_expr and expand: when called directly (e.g., in unit tests), FastAPI
    # Query defaults aren't resolved by dependency injection, so guard against it.
    if not isinstance(filter_expr, str):
        filter_expr = None
    if not isinstance(expand, str):
        expand = None

    user_filter: RuleFilter | None = None
    if filter_expr:
        try:
            validate_filter_expression(filter_expr, schema)
            # Build computed fields map so ?filter=computed_field > X works
            _dialect = session.bind.dialect.name if session.bind and hasattr(session.bind, "dialect") else "sqlite"
            _computed_parts, _computed_params = _build_computed_select_parts(schema, _dialect)
            _computed_map = {name: sql for sql, name in _computed_parts}
            filter_sql, filter_params = compile_filter_to_sql(filter_expr, computed_fields_map=_computed_map)
            if filter_sql != "1=1":
                user_filter = RuleFilter(sql=filter_sql, params=filter_params)
        except (RuleSyntaxError, FilterCompilationError) as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid filter expression",
                    "message": str(exc),
                },
            )

    # 5. Query records
    record_repo = RecordRepository(session)

    # Resolve account; superadmin passes None to see all records across accounts
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = None if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID) else target_account_id

    if is_cursor_mode:
        records, next_cursor, prev_cursor, has_more, total = await record_repo.find_all_cursor(
            collection_name=collection,
            account_id=repo_account_id,
            schema=schema,
            limit=limit,
            sort_by=sort_by,
            descending=descending,
            user_filter=user_filter,
            rule_filter=rule_result,
            cursor_sort_value=cursor_sort_value,
            cursor_record_id=cursor_record_id,
            is_backward=is_backward,
            include_count=include_count,
        )
    else:
        records, total = await record_repo.find_all(
            collection_name=collection,
            account_id=repo_account_id,
            schema=schema,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            descending=descending,
            user_filter=user_filter,
            rule_filter=rule_result,
        )
        next_cursor = None
        prev_cursor = None
        has_more = False

    # 6. Apply field filtering based on permissions
    if allowed_fields != "*":
        filtered_records = []
        for record in records:
            filtered_record = apply_field_filter(record, allowed_fields)
            filtered_records.append(filtered_record)
        records = filtered_records

    # 7. Apply PII masking to all records
    masked_records = []
    for record in records:
        masked_record = _mask_record_pii(
            record, schema,
            current_user.groups if current_user else [],
            current_user.account_id if current_user else None,
        )
        masked_records.append(masked_record)
    records = masked_records

    # 7b. Expand reference fields if requested
    if expand:
        expand_paths, invalid_field = _parse_expand_param(expand, schema)
        if invalid_field is not None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid expand field",
                    "message": f"Field '{invalid_field}' is not a reference field and cannot be expanded",
                },
            )
        if expand_paths:
            from snackbase.core.config import get_settings
            max_depth = get_settings().max_expand_depth
            records = await _expand_records(
                records=records,
                expand_paths=expand_paths,
                schema=schema,
                account_id=repo_account_id,
                collection_repo=collection_repo,
                record_repo=record_repo,
                depth=0,
                max_depth=max_depth,
            )

    # 8. Apply additional field limiting if requested via query param
    # Note: '*' means all fields, skip filtering in that case
    if fields and fields.strip() != "*":
        field_list = [f.strip() for f in fields.split(",")]
        # Always include system fields - RecordResponse requires them
        system_fields = {"id", "account_id", "created_at", "updated_at", "created_by", "updated_by"}
        field_list = list(set(field_list) | system_fields)

        filtered_records = []
        for record in records:
            filtered_record = {k: v for k, v in record.items() if k in field_list}
            filtered_records.append(filtered_record)
        records = filtered_records

    # 9. Return response
    # Debug: Log records before response creation
    logger.debug(f"Creating response with {len(records)} records")
    for i, r in enumerate(records):
        logger.debug(f"Record {i}: keys={list(r.keys())}, id={r.get('id')}")

    response_items = []
    for r in records:
        try:
            response_items.append(RecordResponse.from_record(r))
        except Exception as e:
            logger.error(f"Failed to create RecordResponse for record: {r}", error=str(e))
            raise

    if is_cursor_mode:
        return CursorListResponse(
            items=response_items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            total=total if include_count else None,
        )
    else:
        return RecordListResponse(
            items=response_items,
            total=total,
            skip=skip,
            limit=limit,
        )


# ── Aggregate endpoint — MUST be registered before /{collection}/{record_id} ──
# Starlette matches routes in registration order. "aggregate" must appear as a
# literal path segment before the parameterized {record_id} catch-all.


@router.get(
    "/{collection}/aggregate",
    response_model=AggregationResponse,
    responses={
        400: {"description": "Invalid aggregation expression, unknown field, or type mismatch"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Collection not found"},
    },
)
async def aggregate_collection(
    collection: str,
    request: Request,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    functions: str = Query(..., description='Comma-separated aggregation functions, e.g. "count(),sum(price)"'),
    group_by: str | None = Query(None, description='Comma-separated group-by fields, e.g. "status,category"'),
    filter_expr: str | None = Query(None, alias="filter", description="Pre-aggregation filter expression"),
    having: str | None = Query(None, description="Post-aggregation filter on aggregate aliases, e.g. count() > 5"),
    session: AsyncSession = Depends(get_db_session),
) -> AggregationResponse | JSONResponse:
    """Run aggregation queries (COUNT, SUM, AVG, MIN, MAX) on a collection.

    Supports GROUP BY, HAVING, and pre-aggregation filtering. Respects account
    isolation and collection list_rule permissions.
    """
    # 1. Permission check — same as list_records
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="list",
        session=session,
    )

    # 2. Collection lookup
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)
    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Collection not found", "message": f"Collection '{collection}' does not exist"},
        )

    # 3. Parse schema
    schema = json.loads(collection_model.schema)
    schema_lookup = {f["name"]: f for f in schema}

    # 4. Parse and validate aggregation functions
    try:
        agg_functions = parse_agg_functions(functions, schema_lookup)
    except AggregationParseError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid aggregation functions", "message": str(exc)},
        )

    # 5. Parse and validate group_by
    group_by_fields: list[str] = []
    if group_by:
        try:
            group_by_fields = validate_group_by(group_by, schema_lookup)
        except AggregationParseError as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid group_by", "message": str(exc)},
            )

    # 6. Compile pre-aggregation filter
    user_filter: RuleFilter | None = None
    if filter_expr:
        try:
            validate_filter_expression(filter_expr, schema)
            # Build computed fields map so ?filter=computed_field > X works
            _dialect = session.bind.dialect.name if session.bind and hasattr(session.bind, "dialect") else "sqlite"
            _computed_parts, _computed_params = _build_computed_select_parts(schema, _dialect)
            _computed_map = {name: sql for sql, name in _computed_parts}
            filter_sql, filter_params = compile_filter_to_sql(filter_expr, computed_fields_map=_computed_map)
            if filter_sql != "1=1":
                user_filter = RuleFilter(sql=filter_sql, params=filter_params)
        except (RuleSyntaxError, FilterCompilationError) as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid filter expression", "message": str(exc)},
            )

    # 7. Parse HAVING clause
    having_sql: str | None = None
    having_params: dict[str, Any] = {}
    if having:
        alias_to_sql = {agg.alias: agg.sql_expr for agg in agg_functions}
        try:
            having_sql, having_params = parse_having(having, alias_to_sql)
        except AggregationParseError as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid having expression", "message": str(exc)},
            )

    # 8. Resolve account ID (superadmin sees all accounts)
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = (
        None
        if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID)
        else target_account_id
    )

    # 9. Run aggregation
    record_repo = RecordRepository(session)
    results, total_groups = await record_repo.aggregate_records(
        collection_name=collection,
        account_id=repo_account_id,
        agg_functions=agg_functions,
        group_by_fields=group_by_fields,
        user_filter=user_filter,
        rule_filter=rule_result,
        having_sql=having_sql,
        having_params=having_params,
        schema=schema,
    )

    return AggregationResponse(results=results, total_groups=total_groups)


# ── Batch endpoints — MUST be registered before /{collection}/{record_id} ────
# Starlette matches routes in registration order. Placing POST/PATCH/DELETE
# /{collection}/batch here (before the parameterized /{record_id} routes below)
# ensures "batch" is matched as a literal path segment, not as a record ID.


@router.post(
    "/{collection}/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=BatchCreateResponse,
    responses={
        400: {"model": BatchValidationError, "description": "Validation error on one record"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Collection not found"},
    },
)
async def batch_create_records(
    collection: str,
    request: Request,
    body: BatchCreateRequest,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> BatchCreateResponse | JSONResponse:
    """Batch create records in a collection (atomic — all succeed or all fail).

    Validates all records upfront before writing any. Returns the index of the
    first failing record if validation fails.
    """
    settings = get_settings()
    if len(body.records) > settings.batch_max_size:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "batch_too_large",
                "message": f"Batch size {len(body.records)} exceeds maximum of {settings.batch_max_size}",
            },
        )

    target_account_id = await _resolve_account_id(current_user, request, session)

    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)
    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not found", "message": f"Collection '{collection}' not found"},
        )

    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Failed to parse collection schema"},
        )

    # Check permission once per collection
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="create",
        session=session,
    )
    allowed_fields = rule_result.allowed_fields

    record_repo = RecordRepository(session)
    validated_records: list[dict[str, Any]] = []

    # Validate ALL records upfront before writing any
    for i, raw in enumerate(body.records):
        data = dict(raw)

        validate_request_fields(data, allowed_fields, "create")
        if allowed_fields != "*":
            data = apply_field_filter(data, allowed_fields, is_request=True)

        # Validate reference fields
        reference_errors = []
        for field in schema:
            field_name = field["name"]
            field_type = field.get("type", "text").lower()
            if field_type == FieldType.REFERENCE.value and field_name in data:
                ref_value = data[field_name]
                if ref_value is not None:
                    target_col = field.get("collection", "")
                    exists = await record_repo.check_reference_exists(
                        target_col, ref_value, target_account_id
                    )
                    if not exists:
                        reference_errors.append({
                            "field": field_name,
                            "message": f"Referenced record '{ref_value}' not found in collection '{target_col}'",
                            "code": "invalid_reference",
                        })

        processed_data, validation_errors = RecordValidator.validate_and_apply_defaults(data, schema)

        all_errors = [
            RecordValidationErrorDetail(field=e.field, message=e.message, code=e.code)
            for e in validation_errors
        ] + [RecordValidationErrorDetail(**e) for e in reference_errors]

        if all_errors:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=BatchValidationError(
                    error="validation_error",
                    index=i,
                    details=all_errors,
                ).model_dump(),
            )

        validated_records.append(processed_data)

    # All valid — write atomically
    try:
        created = await record_repo.batch_insert_records(
            collection_name=collection,
            account_id=target_account_id,
            created_by=current_user.user_id if current_user else ANONYMOUS_USER_ID,
            records_data=validated_records,
            schema=schema,
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Batch create failed", collection=collection, error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Batch create failed"},
        )

    # Broadcast a create event for each record
    try:
        broadcaster = request.app.state.event_broadcaster
        for r in created:
            await broadcaster.publish_event(
                account_id=target_account_id,
                collection=collection,
                operation="create",
                data=r,
            )
    except Exception as e:
        logger.error("Failed to broadcast batch create events", error=str(e))

    # Build response — apply field filter + PII masking
    response_records = []
    for r in created:
        if allowed_fields != "*":
            r = apply_field_filter(r, allowed_fields)
        r = _mask_record_pii(
            r, schema,
            current_user.groups if current_user else [],
            current_user.account_id if current_user else None,
        )
        response_records.append(RecordResponse.from_record(r))

    return BatchCreateResponse(created=response_records, count=len(response_records))


@router.patch(
    "/{collection}/batch",
    response_model=BatchUpdateResponse,
    responses={
        400: {"model": BatchValidationError, "description": "Validation error on one record"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "One or more record IDs not found"},
    },
)
async def batch_update_records(
    collection: str,
    request: Request,
    body: BatchUpdateRequest,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> BatchUpdateResponse | JSONResponse:
    """Batch patch records (atomic — all succeed or all fail).

    Returns 404 if any record ID does not exist. The entire batch fails in
    that case so no records are modified.
    """
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

    settings = get_settings()
    if len(body.records) > settings.batch_max_size:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "batch_too_large",
                "message": f"Batch size {len(body.records)} exceeds maximum of {settings.batch_max_size}",
            },
        )

    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = (
        None
        if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID)
        else target_account_id
    )

    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)
    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not found", "message": f"Collection '{collection}' not found"},
        )

    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Failed to parse collection schema"},
        )

    record_repo = RecordRepository(session)

    # Pre-fetch all existing records in one query for 404 checking and audit data
    all_ids = [item.id for item in body.records]
    existing_map = await record_repo.get_by_ids(
        collection_name=collection,
        ids=all_ids,
        account_id=repo_account_id,
        schema=schema,
    )

    # Return 404 if any record is missing (spec: entire batch fails)
    for i, item in enumerate(body.records):
        if item.id not in existing_map:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "not_found",
                    "message": f"Record '{item.id}' not found (index {i})",
                },
            )

    # Check update permission
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="update",
        session=session,
    )
    allowed_fields = rule_result.allowed_fields

    # Validate all updates upfront
    validated_updates: list[dict[str, Any]] = []
    for i, item in enumerate(body.records):
        data = dict(item.data)

        validate_request_fields(data, allowed_fields, "update")
        if allowed_fields != "*":
            data = apply_field_filter(data, allowed_fields, is_request=True)

        processed_data, validation_errors = RecordValidator.validate_and_apply_defaults(
            data, schema, partial=True
        )

        all_errors = [
            RecordValidationErrorDetail(field=e.field, message=e.message, code=e.code)
            for e in validation_errors
        ]

        if all_errors:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=BatchValidationError(
                    error="validation_error",
                    index=i,
                    details=all_errors,
                ).model_dump(),
            )

        validated_updates.append({
            "id": item.id,
            "data": processed_data,
            "old_values": existing_map[item.id],
        })

    # Atomic write
    try:
        updated = await record_repo.batch_update_records(
            collection_name=collection,
            account_id=repo_account_id,
            updated_by=current_user.user_id if current_user else ANONYMOUS_USER_ID,
            updates=validated_updates,
            schema=schema,
            rule_filter=rule_result if rule_result.sql else None,
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Batch update failed", collection=collection, error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Batch update failed"},
        )

    # Broadcast update events
    try:
        broadcaster = request.app.state.event_broadcaster
        for r in updated:
            await broadcaster.publish_event(
                account_id=target_account_id,
                collection=collection,
                operation="update",
                data=r,
            )
    except Exception as e:
        logger.error("Failed to broadcast batch update events", error=str(e))

    # Build response
    response_records = []
    for r in updated:
        if allowed_fields != "*":
            r = apply_field_filter(r, allowed_fields)
        r = _mask_record_pii(
            r, schema,
            current_user.groups if current_user else [],
            current_user.account_id if current_user else None,
        )
        response_records.append(RecordResponse.from_record(r))

    return BatchUpdateResponse(updated=response_records, count=len(response_records))


@router.delete(
    "/{collection}/batch",
    response_model=BatchDeleteResponse,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "One or more record IDs not found"},
    },
)
async def batch_delete_records(
    collection: str,
    request: Request,
    body: BatchDeleteRequest,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> BatchDeleteResponse | JSONResponse:
    """Batch delete records (atomic — all succeed or all fail).

    Returns 404 if any record ID does not exist. The entire batch fails in
    that case so no records are deleted.
    """
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

    settings = get_settings()
    if len(body.ids) > settings.batch_max_size:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "batch_too_large",
                "message": f"Batch size {len(body.ids)} exceeds maximum of {settings.batch_max_size}",
            },
        )

    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = (
        None
        if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID)
        else target_account_id
    )

    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)
    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not found", "message": f"Collection '{collection}' not found"},
        )

    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Failed to parse collection schema"},
        )

    record_repo = RecordRepository(session)

    # Pre-fetch all existing records for 404 checking and hook/audit data
    existing_map = await record_repo.get_by_ids(
        collection_name=collection,
        ids=body.ids,
        account_id=repo_account_id,
        schema=schema,
    )

    # Return 404 if any record is missing (spec: entire batch fails)
    for i, rid in enumerate(body.ids):
        if rid not in existing_map:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "not_found",
                    "message": f"Record '{rid}' not found (index {i})",
                },
            )

    # Check delete permission
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="delete",
        session=session,
    )

    # Atomic delete
    try:
        deleted_ids = await record_repo.batch_delete_records(
            collection_name=collection,
            account_id=repo_account_id,
            record_ids=body.ids,
            records_data=existing_map,
            rule_filter=rule_result if rule_result.sql else None,
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Batch delete failed", collection=collection, error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Batch delete failed"},
        )

    # Broadcast delete events
    try:
        broadcaster = request.app.state.event_broadcaster
        for rid in deleted_ids:
            await broadcaster.publish_event(
                account_id=target_account_id,
                collection=collection,
                operation="delete",
                data={"id": rid},
            )
    except Exception as e:
        logger.error("Failed to broadcast batch delete events", error=str(e))

    return BatchDeleteResponse(deleted=deleted_ids, count=len(deleted_ids))


@router.get(
    "/{collection}/{record_id}",
    response_model=RecordResponse,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Record not found"},
    },
)
async def get_record(
    collection: str,
    record_id: str,
    request: Request,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    expand: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Get a single record by ID."""
    # 1. Look up collection (to get schema for type conversion)
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Collection '{collection}' not found",
            },
        )

    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
         return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Invalid collection schema"},
        )

    # 2. Get record (with view filter)
    # First resolve permission/rule filter
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="view",
        session=session,
    )
    allowed_fields = rule_result.allowed_fields

    record_repo = RecordRepository(session)

    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = None if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID) else target_account_id

    record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=repo_account_id,
        schema=schema,
        rule_filter=rule_result,
    )

    if record is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Record not found",
            },
        )

    # 3. Apply field filter to response
    if allowed_fields != "*":
        record = apply_field_filter(record, allowed_fields)

    # 5. Apply PII masking to response
    record = _mask_record_pii(
        record, schema,
        current_user.groups if current_user else [],
        current_user.account_id if current_user else None,
    )

    # 6. Expand reference fields if requested
    if not isinstance(expand, str):
        expand = None
    if expand:
        expand_paths, invalid_field = _parse_expand_param(expand, schema)
        if invalid_field is not None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid expand field",
                    "message": f"Field '{invalid_field}' is not a reference field and cannot be expanded",
                },
            )
        if expand_paths:
            from snackbase.core.config import get_settings
            max_depth = get_settings().max_expand_depth
            expanded = await _expand_records(
                records=[record],
                expand_paths=expand_paths,
                schema=schema,
                account_id=repo_account_id,
                collection_repo=collection_repo,
                record_repo=record_repo,
                depth=0,
                max_depth=max_depth,
            )
            record = expanded[0]

    return RecordResponse.from_record(record)


@router.put(
    "/{collection}/{record_id}",
    response_model=RecordResponse,
    responses={
        400: {"model": RecordValidationErrorResponse, "description": "Validation error"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Record or collection not found"},
    },
)
async def update_record_full(
    collection: str,
    record_id: str,
    request: Request,
    data: dict[str, Any],
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Update a record (full replacement).

    Replaces the entire record with the provided data (except system fields).
    """
    return await _update_record(collection, record_id, request, data, current_user, auth_context, session, partial=False)


@router.patch(
    "/{collection}/{record_id}",
    response_model=RecordResponse,
    responses={
        400: {"model": RecordValidationErrorResponse, "description": "Validation error"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Record or collection not found"},
    },
)
async def update_record_partial(
    collection: str,
    record_id: str,
    request: Request,
    data: dict[str, Any],
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Update a record (partial update).

    Updates only the provided fields.
    """
    return await _update_record(collection, record_id, request, data, current_user, auth_context, session, partial=True)


async def _update_record(
    collection: str,
    record_id: str,
    request: Request,
    data: dict[str, Any],
    current_user: AuthenticatedUser | None,
    auth_context: AuthorizationContext,
    session: AsyncSession,
    partial: bool,
) -> RecordResponse | JSONResponse:
    """Internal helper for record updates."""
    # 1. Look up collection
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Collection '{collection}' not found",
            },
        )

    # 2. Parse collection schema
    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to parse collection schema",
            },
        )

    # 3. Fetch existing record for permission check context
    record_repo = RecordRepository(session)

    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = None if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID) else target_account_id

    existing_record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=repo_account_id,
        schema=schema,
    )

    if existing_record is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Record not found",
            },
        )

    # 4. Check update permission
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="update",
        session=session,
        record=existing_record,
        request_data=data,
    )
    allowed_fields = rule_result.allowed_fields

    # Validate request fields (reject if contains unauthorized fields)
    validate_request_fields(data, allowed_fields, "update")

    # Filter request body to allowed fields only
    if allowed_fields != "*":
        data = apply_field_filter(data, allowed_fields, is_request=True)

    # 5. Validate reference fields
    reference_errors = []

    # Check references only for fields present in data
    # (if full update, this covers all refs; if partial, only updated refs)
    for field in schema:
        field_name = field["name"]
        field_type = field.get("type", "text").lower()

        if field_type == FieldType.REFERENCE.value and field_name in data:
            ref_value = data[field_name]
            if ref_value is not None:
                target_collection = field.get("collection", "")
                exists = await record_repo.check_reference_exists(
                    target_collection,
                    ref_value,
                    target_account_id,
                )
                if not exists:
                    reference_errors.append({
                        "field": field_name,
                        "message": f"Referenced record '{ref_value}' not found in collection '{target_collection}'",
                        "code": "invalid_reference",
                    })

    # 6. Validate record data
    processed_data, validation_errors = RecordValidator.validate_and_apply_defaults(
        data, schema, partial=partial
    )

    # Combine errors
    all_errors = [
        RecordValidationErrorDetail(
            field=e.field,
            message=e.message,
            code=e.code,
        )
        for e in validation_errors
    ] + [
        RecordValidationErrorDetail(**e) for e in reference_errors
    ]

    if all_errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=RecordValidationErrorResponse(
                error="Validation error",
                details=all_errors,
            ).model_dump(),
        )

    # 7. Update record
    try:
        updated_record = await record_repo.update_record(
            collection_name=collection,
            record_id=record_id,
            account_id=repo_account_id,
            updated_by=current_user.user_id if current_user else ANONYMOUS_USER_ID,
            data=processed_data,
            schema=schema,
            old_values=existing_record,
            rule_filter=rule_result,
        )

        if updated_record is None:
            # Either record doesn't exist or doesn't belong to account
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Not found",
                    "message": "Record not found",
                },
            )

        await session.commit()
    except Exception as e:
        logger.error(
            "Record update failed: database error",
            collection=collection,
            record_id=record_id,
            error=str(e),
        )
        # Check for constraint errors
        error_msg = str(e).lower()
        if "foreign key" in error_msg or "constraint" in error_msg:
             return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": "Foreign key constraint violation",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to update record",
            },
        )

    logger.info(
        "Record updated successfully",
        collection=collection,
        record_id=record_id,
        account_id=target_account_id,
        updated_by=current_user.user_id if current_user else None,
    )

    # 7.5 Broadcast update event
    try:
        broadcaster = request.app.state.event_broadcaster
        await broadcaster.publish_event(
            account_id=target_account_id,
            collection=collection,
            operation="update",
            data=updated_record
        )
    except Exception as e:
        logger.error("Failed to broadcast update event", error=str(e))

    # 8. Apply field filter to response
    if allowed_fields != "*":
        updated_record = apply_field_filter(updated_record, allowed_fields)

    # 9. Apply PII masking to response
    updated_record = _mask_record_pii(
        updated_record, schema,
        current_user.groups if current_user else [],
        current_user.account_id if current_user else None,
    )

    return RecordResponse.from_record(updated_record)


@router.delete(
    "/{collection}/{record_id}",
    responses={
        204: {"description": "Record deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Record or collection not found"},
        409: {"description": "Conflict (Foreign Key Restriction)"},
    },
)
async def delete_record(
    collection: str,
    record_id: str,
    request: Request,
    current_user: OptionalUser,
    auth_context: OptionalAuthContext,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a record by ID."""
    from fastapi import Response

    # 1. Look up collection
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": f"Collection '{collection}' not found",
            },
        )

    # 2. Parse schema
    try:
        schema = json.loads(collection_model.schema)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Invalid collection schema"},
        )

    # 3. Fetch record for permission check context
    record_repo = RecordRepository(session)

    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    target_account_id = await _resolve_account_id(current_user, request, session)
    repo_account_id = None if (current_user is not None and current_user.account_id == SYSTEM_ACCOUNT_ID) else target_account_id

    record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=repo_account_id,
        schema=schema,
    )

    if record is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Record not found",
            },
        )

    # 4. Check delete permission
    rule_result = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="delete",
        session=session,
        record=record,
    )

    # 5. Delete record
    try:
        deleted = await record_repo.delete_record(
            collection_name=collection,
            record_id=record_id,
            account_id=repo_account_id,
            record_data=record,
            rule_filter=rule_result,
        )

        if not deleted:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Not found",
                    "message": "Record not found",
                },
            )

        await session.commit()

        logger.info(
            "Record deleted successfully",
            collection=collection,
            record_id=record_id,
            account_id=target_account_id,
            deleted_by=current_user.user_id if current_user else None,
        )

        # Broadcast delete event
        try:
            broadcaster = request.app.state.event_broadcaster
            await broadcaster.publish_event(
                account_id=target_account_id,
                collection=collection,
                operation="delete",
                data={"id": record_id}
            )
        except Exception as e:
            logger.error("Failed to broadcast delete event", error=str(e))

        # Return 204 No Content
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(
            "Record deletion failed",
            collection=collection,
            record_id=record_id,
            error=str(e),
        )
        # Check for constraint errors
        error_msg = str(e).lower()
        if "foreign key" in error_msg or "constraint" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "Conflict",
                    "message": "Cannot delete record: it is referenced by other records",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to delete record",
            },
        )

