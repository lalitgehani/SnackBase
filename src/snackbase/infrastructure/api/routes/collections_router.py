"""Collections API routes.

Provides endpoints for managing dynamic collections.
"""

import json
import uuid
from typing import cast

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionService, CollectionValidator
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import (
    CollectionListItem,
    CollectionListResponse,
    CollectionResponse,
    CreateCollectionRequest,
    SchemaFieldResponse,
    UpdateCollectionRequest,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=CollectionListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_collections(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=25, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    search: str | None = Query(default=None, description="Search term for name or ID"),
) -> CollectionListResponse:
    """List all collections with pagination and search.

    Only superadmins (users in the SY0000 system account) can list collections.
    """
    collection_repo = CollectionRepository(session)

    # Get collections with pagination
    collections, total = await collection_repo.get_all(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )

    # Build response items
    items = []
    for collection in collections:
        schema = json.loads(collection.schema)
        table_name = TableBuilder.generate_table_name(collection.name)

        # Get record count
        try:
            records_count = await collection_repo.get_record_count(table_name)
        except Exception as e:
            logger.warning(
                "Failed to get record count for collection",
                collection_id=collection.id,
                table_name=table_name,
                error=str(e),
            )
            records_count = 0

        items.append(
            CollectionListItem(
                id=collection.id,
                name=collection.name,
                table_name=table_name,
                fields_count=len(schema),
                records_count=records_count,
                created_at=collection.created_at,
            )
        )

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    logger.info(
        "Collections listed",
        total=total,
        page=page,
        page_size=page_size,
        user_id=current_user.user_id,
    )

    return CollectionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/names",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def get_collection_names(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Get simple list of all collection names.

    Returns a simple list of collection names without pagination,
    suitable for populating dropdowns and permission matrices.
    Only superadmins can access this endpoint.

    Args:
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        List of collection names.
    """
    collection_repo = CollectionRepository(session)
    collections = await collection_repo.list_all()

    names = [collection.name for collection in collections]

    logger.debug(
        "Collection names retrieved",
        count=len(names),
        requested_by=current_user.user_id,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"names": names, "total": len(names)},
    )


@router.get(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    response_model=CollectionResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Collection not found"},
    },
)
async def get_collection(
    collection_id: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionResponse | JSONResponse:
    """Get collection details by ID.

    Only superadmins (users in the SY0000 system account) can view collections.
    """
    collection_repo = CollectionRepository(session)
    collection = await collection_repo.get_by_id(collection_id)

    if not collection:
        logger.info(
            "Collection not found",
            collection_id=collection_id,
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not Found",
                "message": f"Collection with ID '{collection_id}' not found",
            },
        )

    # Parse schema
    schema_dicts = json.loads(collection.schema)
    table_name = TableBuilder.generate_table_name(collection.name)

    logger.info(
        "Collection retrieved",
        collection_id=collection_id,
        collection_name=collection.name,
        user_id=current_user.user_id,
    )

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
        engine = cast(AsyncEngine, session.bind)
        logger.debug(f"Session bind type: {type(session.bind)}, engine: {engine}")
        await TableBuilder.create_table(engine, request.name, schema_dicts)
        logger.info(f"Table created successfully: {table_name}")
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


@router.put(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    response_model=CollectionResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Superadmin access required"},
        404: {"description": "Collection not found"},
    },
)
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionResponse | JSONResponse:
    """Update collection schema.

    Allows adding new fields and modifying field properties (except type changes).
    Only superadmins (users in the SY0000 system account) can update collections.
    """
    # Convert schema to dict list
    schema_dicts = [field.model_dump() for field in request.fields]

    # Use CollectionService for business logic
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    try:
        updated_collection = await collection_service.update_collection_schema(
            collection_id, schema_dicts
        )
        await session.commit()
        await session.refresh(updated_collection)
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            logger.info(
                "Collection update failed: not found",
                collection_id=collection_id,
                user_id=current_user.user_id,
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Not Found",
                    "message": error_message,
                },
            )
        else:
            logger.info(
                "Collection update failed: validation error",
                collection_id=collection_id,
                error=error_message,
                user_id=current_user.user_id,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": error_message,
                },
            )

    table_name = TableBuilder.generate_table_name(updated_collection.name)

    logger.info(
        "Collection updated successfully",
        collection_id=collection_id,
        collection_name=updated_collection.name,
        updated_by=current_user.user_id,
    )

    return CollectionResponse(
        id=updated_collection.id,
        name=updated_collection.name,
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
        created_at=updated_collection.created_at,
        updated_at=updated_collection.updated_at,
    )


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Collection not found"},
    },
)
async def delete_collection(
    collection_id: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Delete collection and drop its physical table.

    Only superadmins (users in the SY0000 system account) can delete collections.
    """
    # Use CollectionService for business logic
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    try:
        result = await collection_service.delete_collection(collection_id)
    except ValueError as e:
        logger.info(
            "Collection deletion failed: not found",
            collection_id=collection_id,
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not Found",
                "message": str(e),
            },
        )

    logger.info(
        "Collection deleted successfully",
        collection_id=collection_id,
        deleted_by=current_user.user_id,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Collection deleted successfully",
            **result,
        },
    )

