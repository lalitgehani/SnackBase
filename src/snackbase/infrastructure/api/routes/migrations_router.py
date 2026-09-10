"""Migration query API routes.

Provides read-only endpoints for viewing Alembic migration status and history.
"""

from typing import Any, cast

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.application.services.migration_query_service import MigrationQueryService
from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas.migration_query_schemas import (
    CurrentRevisionResponse,
    DeclaredCollection,
    MigrationGenerateRequest,
    MigrationGenerateResponse,
    MigrationHistoryItemResponse,
    MigrationHistoryResponse,
    MigrationListResponse,
    MigrationPlanRequest,
    MigrationPlanResponse,
    MigrationRevisionResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=MigrationListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_migrations(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> MigrationListResponse | JSONResponse:
    """List all Alembic revisions.

    Returns all migration revisions from both core and dynamic directories
    with their application status.

    Only superadmins can access this endpoint.
    """
    try:
        settings = get_settings()
        engine = cast(AsyncEngine, session.bind)

        service = MigrationQueryService(
            alembic_ini_path="alembic.ini",
            database_url=settings.database_url,
            engine=engine,
        )

        revisions_data = await service.get_all_revisions()
        current_revision_data = await service.get_current_revision()

        revisions = [MigrationRevisionResponse(**rev) for rev in revisions_data]
        current_revision = (
            current_revision_data["revision"] if current_revision_data else None
        )

        logger.info(
            "Migrations listed",
            total=len(revisions),
            current=current_revision,
            user_id=current_user.user_id,
        )

        response = MigrationListResponse(
            revisions=revisions,
            total=len(revisions),
            current_revision=current_revision,
        )

        # Add cache headers for performance (cache for 60 seconds)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(),
            headers={
                "Cache-Control": "public, max-age=60",
                "ETag": f'"{current_revision or "none"}"',
            },
        )

    except Exception as e:
        logger.error(
            "Failed to list migrations",
            error=str(e),
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "Failed to retrieve migration list",
            },
        )


@router.get(
    "/current",
    status_code=status.HTTP_200_OK,
    response_model=CurrentRevisionResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "No current revision (database not initialized)"},
    },
)
async def get_current_migration(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CurrentRevisionResponse | JSONResponse:
    """Get current database revision.

    Returns the currently applied migration revision.

    Only superadmins can access this endpoint.
    """
    try:
        settings = get_settings()
        engine = cast(AsyncEngine, session.bind)

        service = MigrationQueryService(
            alembic_ini_path="alembic.ini",
            database_url=settings.database_url,
            engine=engine,
        )

        current_revision_data = await service.get_current_revision()

        if not current_revision_data:
            logger.info(
                "No current revision found",
                user_id=current_user.user_id,
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Not Found",
                    "message": "No current revision found. Database may not be initialized.",
                },
            )

        logger.info(
            "Current migration retrieved",
            revision=current_revision_data["revision"],
            user_id=current_user.user_id,
        )

        response = CurrentRevisionResponse(**current_revision_data)

        # Add cache headers for performance (cache for 60 seconds)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(),
            headers={
                "Cache-Control": "public, max-age=60",
                "ETag": f'"{current_revision_data["revision"]}"',
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get current migration",
            error=str(e),
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "Failed to retrieve current migration",
            },
        )


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    response_model=MigrationHistoryResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def get_migration_history(
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> MigrationHistoryResponse | JSONResponse:
    """Get full migration history.

    Returns all applied migrations in chronological order from oldest to newest.

    Only superadmins can access this endpoint.
    """
    try:
        settings = get_settings()
        engine = cast(AsyncEngine, session.bind)

        service = MigrationQueryService(
            alembic_ini_path="alembic.ini",
            database_url=settings.database_url,
            engine=engine,
        )

        history_data = await service.get_migration_history()

        history = [
            MigrationHistoryItemResponse(
                revision=item["revision"],
                description=item["description"],
                is_dynamic=item["is_dynamic"],
                created_at=item["created_at"],
            )
            for item in history_data
        ]

        logger.info(
            "Migration history retrieved",
            total=len(history),
            user_id=current_user.user_id,
        )

        response = MigrationHistoryResponse(
            history=history,
            total=len(history),
        )

        # Add cache headers for performance (cache for 60 seconds)
        current_revision_data = await service.get_current_revision()
        current_revision = (
            current_revision_data["revision"] if current_revision_data else "none"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(),
            headers={
                "Cache-Control": "public, max-age=60",
                "ETag": f'"{current_revision}"',
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get migration history",
            error=str(e),
            user_id=current_user.user_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "Failed to retrieve migration history",
            },
        )


def _declared_map(
    request_collections: list[DeclaredCollection],
) -> dict[str, list[dict[str, Any]]]:
    return {item.name: [dict(field) for field in item.fields] for item in request_collections}


async def _current_schema_map(session: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    import json

    from snackbase.infrastructure.persistence.repositories import CollectionRepository

    repo = CollectionRepository(session)
    collections = await repo.list_all()
    out: dict[str, list[dict[str, Any]]] = {}
    for collection in collections:
        try:
            out[collection.name] = json.loads(collection.schema)
        except json.JSONDecodeError:
            out[collection.name] = []
    return out


@router.post(
    "/plan",
    status_code=status.HTTP_200_OK,
    response_model=MigrationPlanResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def plan_migrations(
    body: MigrationPlanRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> MigrationPlanResponse:
    """Diff declared collection schemas against the live registry without applying."""
    from snackbase.domain.services.schema_diff import diff_collection_schemas

    current = await _current_schema_map(session)
    declared = _declared_map(body.collections)
    plan = diff_collection_schemas(current, declared)
    logger.info(
        "Migration plan computed",
        added=len(plan.added),
        removed=len(plan.removed),
        changed=len(plan.changed),
        user_id=current_user.user_id,
    )
    return MigrationPlanResponse(**plan.to_dict())


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    response_model=MigrationGenerateResponse,
    responses={
        403: {"description": "Superadmin access required"},
        409: {"description": "Destructive changes require confirm: true"},
    },
)
async def generate_migrations(
    body: MigrationGenerateRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> MigrationGenerateResponse | JSONResponse:
    """Write one Alembic revision implementing the plan and apply it.

    Destructive changes (type change, field removal, unique addition) require
    ``confirm: true``. Without it this endpoint returns 409 and writes nothing.
    """
    import json
    import uuid

    from snackbase.domain.services.schema_diff import diff_collection_schemas
    from snackbase.infrastructure.persistence.migration_service import MigrationService
    from snackbase.infrastructure.persistence.models import CollectionModel
    from snackbase.infrastructure.persistence.models.collection_rule import CollectionRuleModel
    from snackbase.infrastructure.persistence.repositories import CollectionRepository
    from snackbase.infrastructure.persistence.repositories.collection_rule_repository import (
        CollectionRuleRepository,
    )

    current = await _current_schema_map(session)
    declared = _declared_map(body.collections)
    plan = diff_collection_schemas(current, declared)

    if plan.has_destructive() and not body.confirm:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Confirmation required",
                "message": "Destructive changes require confirm: true",
                "plan": plan.to_dict(),
            },
        )

    if plan.is_empty():
        return MigrationGenerateResponse(
            revision=None,
            plan=MigrationPlanResponse(**plan.to_dict()),
            applied=False,
        )

    engine = cast(AsyncEngine, session.bind)
    service = MigrationService(alembic_ini_path="alembic.ini", engine=engine)

    rev_id = service.generate_plan_migration(plan.to_dict(), declared, current)
    await service.apply_migrations()

    repo = CollectionRepository(session)
    rule_repo = CollectionRuleRepository(session)
    for name, fields in declared.items():
        existing = await repo.get_by_name(name)
        if existing is None:
            collection_id = str(uuid.uuid4())
            created = CollectionModel(
                id=collection_id,
                name=name,
                schema=json.dumps(fields),
                migration_revision=rev_id,
            )
            await repo.create(created)
            await rule_repo.create(
                CollectionRuleModel(
                    id=str(uuid.uuid4()),
                    collection_id=collection_id,
                    list_rule=None,
                    view_rule=None,
                    create_rule=None,
                    update_rule=None,
                    delete_rule=None,
                    list_fields="*",
                    view_fields="*",
                    create_fields="*",
                    update_fields="*",
                )
            )
        else:
            existing.schema = json.dumps(fields)
            existing.migration_revision = rev_id

    await session.commit()

    logger.info(
        "Migration generated and applied",
        revision=rev_id,
        user_id=current_user.user_id,
    )
    return MigrationGenerateResponse(
        revision=rev_id,
        plan=MigrationPlanResponse(**plan.to_dict()),
        applied=True,
    )
