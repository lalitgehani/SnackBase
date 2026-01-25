"""Collections API routes.

Provides endpoints for managing dynamic collections.
"""

import json
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import CollectionService
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas import (
    CollectionListItem,
    CollectionListResponse,
    CollectionResponse,
    CreateCollectionRequest,
    SchemaFieldResponse,
    UpdateCollectionRequest,
)
from snackbase.infrastructure.api.schemas.collection_schemas import (
    CollectionImportItemResult,
    CollectionImportRequest,
    CollectionImportResult,
)
from snackbase.infrastructure.persistence.database import get_db_session
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

    Only superadmins (users in the system account) can list collections.
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
    "/export",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Exported collections JSON file",
        },
        403: {"description": "Superadmin access required"},
    },
)
async def export_collections(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
    collection_ids: str | None = Query(
        default=None,
        description="Comma-separated list of collection IDs to export (all if omitted)",
    ),
) -> Response:
    """Export collections to JSON format.

    Exports collection schemas and rules in a portable JSON format.
    Can be used for backups, version control, or migrating between environments.
    Only superadmins can export collections.
    """
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    # Parse collection_ids if provided
    ids_list: list[str] | None = None
    if collection_ids:
        ids_list = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]

    # Export collections
    content, media_type = await collection_service.export_collections(
        user_email=current_user.email or current_user.user_id,
        collection_ids=ids_list,
    )

    # Generate filename
    filename = f"collections_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    logger.info(
        "Collections exported",
        collection_ids=ids_list,
        exported_by=current_user.user_id,
    )

    return Response(content=content, media_type=media_type, headers=headers)


@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
    response_model=CollectionImportResult,
    responses={
        400: {"description": "Invalid JSON or validation error"},
        403: {"description": "Superadmin access required"},
    },
)
async def import_collections(
    request: CollectionImportRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionImportResult | JSONResponse:
    """Import collections from JSON export.

    Imports collection schemas and rules from an export file.
    Supports different strategies for handling existing collections:
    - error: Fail if any collection already exists (safest)
    - skip: Skip existing collections, import only new ones
    - update: Update existing collections with new schema

    Only superadmins can import collections.
    """
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    try:
        # Convert Pydantic model to dict for processing
        export_data = request.data.model_dump(by_alias=True)

        result = await collection_service.import_collections(
            export_data=export_data,
            strategy=request.strategy.value,
            user_id=current_user.user_id,
        )

        await session.commit()

        logger.info(
            "Collections imported",
            imported=result["imported_count"],
            skipped=result["skipped_count"],
            updated=result["updated_count"],
            failed=result["failed_count"],
            imported_by=current_user.user_id,
        )

        return CollectionImportResult(
            success=result["success"],
            imported_count=result["imported_count"],
            skipped_count=result["skipped_count"],
            updated_count=result["updated_count"],
            failed_count=result["failed_count"],
            collections=[CollectionImportItemResult(**c) for c in result["collections"]],
            migrations_created=result["migrations_created"],
        )

    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "message": str(e),
            },
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

    Only superadmins (users in the system account) can view collections.
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

    Creates an Alembic migration and applies it to create the physical table.
    Only superadmins can create collections.
    """
    # Convert schema to dict list
    schema_dicts = [field.model_dump() for field in request.fields]

    # Use CollectionService for business logic
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    # Extract rules from request
    rules_data = {
        "list_rule": request.list_rule,
        "view_rule": request.view_rule,
        "create_rule": request.create_rule,
        "update_rule": request.update_rule,
        "delete_rule": request.delete_rule,
        "list_fields": request.list_fields,
        "view_fields": request.view_fields,
        "create_fields": request.create_fields,
        "update_fields": request.update_fields,
    }

    try:
        collection = await collection_service.create_collection(
            request.name, schema_dicts, current_user.user_id, rules_data=rules_data
        )
        await session.commit()
        await session.refresh(collection)
    except ValueError as e:
        error_message = str(e)
        if "already exists" in error_message.lower():
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "Conflict",
                    "message": error_message,
                    "field": "name",
                },
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": error_message,
                },
            )

    table_name = TableBuilder.generate_table_name(collection.name)

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
    Only superadmins (users in the system account) can update collections.
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

    Uses a two-phase approach to avoid transaction deadlocks on PostgreSQL:
    1. Prepare deletion and generate migration (read-only)
    2. Close session and apply migration (no locks held)
    3. Delete collection record in new session

    Only superadmins (users in the system account) can delete collections.
    """
    # Phase 1: Prepare deletion and generate migration
    engine = cast(AsyncEngine, session.bind)
    collection_service = CollectionService(session, engine)

    try:
        result = await collection_service.prepare_collection_deletion(collection_id)
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

    # Phase 2: Close session and apply migration (no locks held)
    await session.close()

    try:
        logger.info("Applying migration", revision=result["migration_revision"])
        await collection_service.migration_service.apply_migrations()
    except Exception as e:
        logger.error(
            "Migration failed during collection deletion",
            collection_id=collection_id,
            revision=result["migration_revision"],
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Migration Failed",
                "message": f"Failed to drop table: {str(e)}",
            },
        )

    # Phase 3: Delete collection record in new session
    # Create new session from the same engine to ensure we're using the correct database
    from sqlalchemy.orm import sessionmaker
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as new_session:
        new_collection_service = CollectionService(new_session, engine)
        try:
            await new_collection_service.finalize_collection_deletion(collection_id)
            await new_session.commit()
        except ValueError as e:
            logger.error(
                "Failed to delete collection record after migration",
                collection_id=collection_id,
                error=str(e),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Deletion Failed",
                    "message": f"Table dropped but failed to delete collection record: {str(e)}",
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

