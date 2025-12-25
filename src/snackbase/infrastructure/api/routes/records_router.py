"""Records API routes.

Provides dynamic endpoints for CRUD operations on collection records.
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import FieldType, RecordValidator
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, AuthContext
from snackbase.infrastructure.api.middleware import (
    check_collection_permission,
    apply_field_filter,
)
from snackbase.infrastructure.api.schemas import (
    RecordResponse,
    RecordValidationErrorDetail,
    RecordValidationErrorResponse,
    RecordListResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    RecordRepository,
)

logger = get_logger(__name__)

router = APIRouter()


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
    data: dict[str, Any],
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Create a new record in a collection.

    Validates the request data against the collection schema, auto-generates
    a record ID, and sets system fields (account_id, created_at, created_by).

    Args:
        collection: The collection name (from URL path).
        data: The record data (request body).
        current_user: The authenticated user.
        auth_context: Authorization context for permission checking.
        session: Database session.

    Returns:
        The created record with all fields including system fields.
    """
    # 0. Check create permission
    allowed, allowed_fields = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="create",
        session=session,
    )
    
    # Filter request body to allowed fields only
    if allowed_fields != "*":
        data = apply_field_filter(data, allowed_fields)
    
    # 1. Look up collection by name
    collection_repo = CollectionRepository(session)
    collection_model = await collection_repo.get_by_name(collection)

    if collection_model is None:
        logger.info(
            "Record creation failed: collection not found",
            collection=collection,
            user_id=current_user.user_id,
        )
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

    # 3. Validate reference fields (check if referenced records exist)
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
                    current_user.account_id,
                )
                if not exists:
                    reference_errors.append({
                        "field": field_name,
                        "message": f"Referenced record '{ref_value}' not found in collection '{target_collection}'",
                        "code": "invalid_reference",
                    })

    # 4. Validate record data against schema
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
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=RecordValidationErrorResponse(
                error="Validation error",
                details=all_errors,
            ).model_dump(),
        )

    # 5. Generate record ID
    record_id = str(uuid.uuid4())

    # 6. Insert record
    try:
        created_record = await record_repo.insert_record(
            collection_name=collection,
            record_id=record_id,
            account_id=current_user.account_id,
            created_by=current_user.user_id,
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
        account_id=current_user.account_id,
        created_by=current_user.user_id,
    )

    # 7. Apply field filter to response
    if allowed_fields != "*":
        created_record = apply_field_filter(created_record, allowed_fields)
    
    return RecordResponse.from_record(created_record)


@router.get(
    "/{collection}",
    response_model=RecordListResponse,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        404: {"description": "Collection not found"},
    },
)
async def list_records(
    collection: str,
    request: Request,
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("-created_at"),
    fields: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> RecordListResponse | JSONResponse:
    """List records in a collection.

    Supports pagination, sorting, and filtering.
    """
    # 0. Check read permission
    allowed, allowed_fields = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="read",
        session=session,
    )
    
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

    # 4. Extract filters from query params
    # Exclude reserved params
    reserved_params = {"skip", "limit", "sort", "fields"}
    filters = {
        k: v for k, v in request.query_params.items() 
        if k not in reserved_params
    }

    # 5. Query records
    record_repo = RecordRepository(session)
    records, total = await record_repo.find_all(
        collection_name=collection,
        account_id=current_user.account_id,
        schema=schema,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        descending=descending,
        filters=filters,
    )

    # 6. Apply field filtering based on permissions
    if allowed_fields != "*":
        filtered_records = []
        for record in records:
            filtered_record = apply_field_filter(record, allowed_fields)
            filtered_records.append(filtered_record)
        records = filtered_records
    
    # 7. Apply additional field limiting if requested via query param
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        # Always include ID
        if "id" not in field_list:
            field_list.append("id")
            
        filtered_records = []
        for record in records:
            filtered_record = {k: v for k, v in record.items() if k in field_list}
            filtered_records.append(filtered_record)
        records = filtered_records

    # 8. Return response
    return RecordListResponse(
        items=[RecordResponse.from_record(r) for r in records],
        total=total,
        skip=skip,
        limit=limit,
    )


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
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
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

    # 2. Get record
    record_repo = RecordRepository(session)
    record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=current_user.account_id,
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
    
    # 3. Check read permission with record context
    allowed, allowed_fields = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="read",
        session=session,
        record=record,
    )
    
    # 4. Apply field filter to response
    if allowed_fields != "*":
        record = apply_field_filter(record, allowed_fields)

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
    data: dict[str, Any],
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Update a record (full replacement).
    
    Replaces the entire record with the provided data (except system fields).
    """
    return await _update_record(collection, record_id, data, current_user, auth_context, session, partial=False)


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
    data: dict[str, Any],
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Update a record (partial update).
    
    Updates only the provided fields.
    """
    return await _update_record(collection, record_id, data, current_user, auth_context, session, partial=True)


async def _update_record(
    collection: str,
    record_id: str,
    data: dict[str, Any],
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
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
    existing_record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=current_user.account_id,
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
    
    # 4. Check update permission with record context
    allowed, allowed_fields = await check_collection_permission(
        auth_context=auth_context,
        collection=collection,
        operation="update",
        session=session,
        record=existing_record,
    )
    
    # Filter request body to allowed fields only
    if allowed_fields != "*":
        data = apply_field_filter(data, allowed_fields)

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
                    current_user.account_id,
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
            account_id=current_user.account_id,
            updated_by=current_user.user_id,
            data=processed_data,
            schema=schema,
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
        account_id=current_user.account_id,
        updated_by=current_user.user_id,
    )
    
    # 8. Apply field filter to response
    if allowed_fields != "*":
        updated_record = apply_field_filter(updated_record, allowed_fields)

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
    current_user: AuthenticatedUser,
    auth_context: AuthContext,
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
    record = await record_repo.get_by_id(
        collection_name=collection,
        record_id=record_id,
        account_id=current_user.account_id,
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
    
    # 4. Check delete permission with record context
    await check_collection_permission(
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
            account_id=current_user.account_id,
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
            account_id=current_user.account_id,
            deleted_by=current_user.user_id,
        )
        
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

