"""Collections API routes.

Provides endpoints for managing dynamic collections.
"""

import json
import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionValidator
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import (
    CollectionResponse,
    CreateCollectionRequest,
    SchemaFieldResponse,
)
from snackbase.infrastructure.persistence.database import get_db_manager, get_db_session
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CollectionResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Superadmin access required"},
        409: {"description": "Collection already exists"},
    },
)
async def create_collection(
    request: CreateCollectionRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionResponse | JSONResponse:
    """Create a new collection with custom schema.

    Creates a physical database table and stores the collection definition.
    Only superadmins (users in the SY0000 system account) can create collections.

    Flow:
    1. Validate collection name
    2. Validate schema fields
    3. Check collection name uniqueness
    4. Generate unique table name
    5. Create physical table with auto-added system columns
    6. Store collection definition in collections table
    7. Return created collection

    Auto-added columns:
    - id (TEXT PRIMARY KEY)
    - account_id (TEXT NOT NULL)
    - created_at (DATETIME)
    - created_by (TEXT)
    - updated_at (DATETIME)
    - updated_by (TEXT)
    """
    # Convert schema to dict list for validation
    schema_dicts = [field.model_dump() for field in request.fields]

    # 1 & 2. Validate collection name and schema
    validation_errors = CollectionValidator.validate(request.name, schema_dicts)
    if validation_errors:
        logger.info(
            "Collection creation failed: validation errors",
            collection_name=request.name,
            error_count=len(validation_errors),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "details": [
                    {"field": e.field, "message": e.message, "code": e.code}
                    for e in validation_errors
                ],
            },
        )

    # 3. Check collection name uniqueness
    collection_repo = CollectionRepository(session)
    if await collection_repo.name_exists(request.name):
        logger.info(
            "Collection creation failed: name already exists",
            collection_name=request.name,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Conflict",
                "message": f"Collection '{request.name}' already exists",
                "field": "name",
            },
        )

    # 4. Generate unique table name
    table_name = TableBuilder.generate_table_name(request.name)

    # 5. Create physical table
    try:
        # Use session's engine to ensure we're using the correct database (especially for tests)
        from sqlalchemy.ext.asyncio import AsyncEngine
        from typing import cast
        engine = cast(AsyncEngine, session.bind)
        await TableBuilder.create_table(engine, request.name, schema_dicts)
    except Exception as e:
        logger.error(
            "Collection creation failed: table creation error",
            collection_name=request.name,
            table_name=table_name,
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal error",
                "message": "Failed to create collection table",
            },
        )

    # 6. Store collection definition
    collection_id = str(uuid.uuid4())
    collection = CollectionModel(
        id=collection_id,
        name=request.name,
        schema=json.dumps(schema_dicts),
    )
    await collection_repo.create(collection)
    await session.commit()
    await session.refresh(collection)

    logger.info(
        "Collection created successfully",
        collection_id=collection_id,
        collection_name=request.name,
        table_name=table_name,
        created_by=current_user.user_id,
    )

    # 7. Return response
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        table_name=table_name,
        fields=[
            SchemaFieldResponse(
                name=f["name"],
                type=f["type"],
                required=f.get("required", False),
                default=f.get("default"),
                unique=f.get("unique", False),
                options=f.get("options"),
                collection=f.get("collection"),
                on_delete=f.get("on_delete"),
                pii=f.get("pii", False),
                mask_type=f.get("mask_type"),
            )
            for f in schema_dicts
        ],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )
