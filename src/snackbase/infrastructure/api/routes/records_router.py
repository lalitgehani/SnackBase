"""Records API routes.

Provides dynamic endpoints for CRUD operations on collection records.
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import FieldType, RecordValidator
from snackbase.infrastructure.api.dependencies import AuthenticatedUser
from snackbase.infrastructure.api.schemas import (
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
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse | JSONResponse:
    """Create a new record in a collection.

    Validates the request data against the collection schema, auto-generates
    a record ID, and sets system fields (account_id, created_at, created_by).

    Args:
        collection: The collection name (from URL path).
        data: The record data (request body).
        current_user: The authenticated user.
        session: Database session.

    Returns:
        The created record with all fields including system fields.
    """
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

    # 7. Return created record
    return RecordResponse.from_record(created_record)
