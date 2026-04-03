"""API router for custom endpoint management (F8.2).

Account-scoped CRUD endpoints for managing custom serverless functions.
Each endpoint defines an HTTP path, method, action pipeline, and response template.

Endpoints:
    POST   /                          Create a new custom endpoint
    GET    /                          List endpoints for the account
    GET    /{endpoint_id}             Get a single endpoint
    PATCH  /{endpoint_id}/toggle      Toggle enabled/disabled
    PUT    /{endpoint_id}             Update an endpoint
    DELETE /{endpoint_id}             Delete an endpoint
    GET    /{endpoint_id}/executions  List execution history

Note: /{endpoint_id}/toggle and /{endpoint_id}/executions are registered
before /{endpoint_id} to avoid FastAPI matching literal path segments as IDs.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.endpoint_schemas import (
    EndpointCreateRequest,
    EndpointExecutionListResponse,
    EndpointExecutionResponse,
    EndpointListResponse,
    EndpointResponse,
    EndpointUpdateRequest,
)
from snackbase.infrastructure.persistence.models.endpoint import EndpointModel
from snackbase.infrastructure.persistence.repositories.endpoint_repository import (
    EndpointRepository,
)

router = APIRouter(tags=["Endpoints"])
logger = get_logger(__name__)

_DEFAULT_MAX_ENDPOINTS = 20


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def get_endpoint_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EndpointRepository:
    return EndpointRepository(session)


EndpointRepo = Annotated[EndpointRepository, Depends(get_endpoint_repository)]


def _build_response(endpoint: EndpointModel) -> EndpointResponse:
    return EndpointResponse(
        id=endpoint.id,
        account_id=endpoint.account_id,
        name=endpoint.name,
        description=endpoint.description,
        path=endpoint.path,
        method=endpoint.method,
        auth_required=endpoint.auth_required,
        condition=endpoint.condition,
        actions=endpoint.actions or [],
        response_template=endpoint.response_template,
        enabled=endpoint.enabled,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
        created_by=endpoint.created_by,
    )


def _get_max_endpoints(request: Request) -> int:
    try:
        from snackbase.core.config import get_settings
        settings = get_settings()
        return getattr(settings, "max_endpoints_per_account", _DEFAULT_MAX_ENDPOINTS)
    except Exception:
        return _DEFAULT_MAX_ENDPOINTS


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EndpointResponse)
async def create_endpoint(
    data: EndpointCreateRequest,
    request: Request,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EndpointResponse:
    """Create a new custom endpoint for the current account.

    Returns 409 if the account has reached the endpoint limit, or if a
    conflicting (account_id, path, method) combination already exists.
    Returns 422 if the path is invalid or conflicts with a built-in route.
    """
    max_endpoints = _get_max_endpoints(request)
    current_count = await repo.count_for_account(current_user.account_id)
    if current_count >= max_endpoints:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account has reached the maximum of {max_endpoints} custom endpoints",
        )

    if await repo.exists_by_path_and_method(
        current_user.account_id, data.path, data.method
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An endpoint with path '{data.path}' and method '{data.method}' "
                "already exists for this account"
            ),
        )

    endpoint = EndpointModel(
        account_id=current_user.account_id,
        name=data.name,
        description=data.description,
        path=data.path,
        method=data.method,
        auth_required=data.auth_required,
        condition=data.condition,
        actions=data.actions,
        response_template=data.response_template,
        enabled=data.enabled,
        created_by=current_user.user_id,
    )

    await repo.create(endpoint)
    await session.commit()
    await session.refresh(endpoint)

    logger.info(
        "Custom endpoint created",
        endpoint_id=endpoint.id,
        method=endpoint.method,
        path=endpoint.path,
        account_id=current_user.account_id,
    )
    return _build_response(endpoint)


@router.get("", response_model=EndpointListResponse)
async def list_endpoints(
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    method: str | None = Query(default=None, description="Filter by HTTP method"),
    enabled: bool | None = Query(default=None, description="Filter by enabled status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EndpointListResponse:
    """List custom endpoints for the current account."""
    endpoints, total = await repo.list_for_account(
        account_id=current_user.account_id,
        method=method,
        enabled=enabled,
        offset=offset,
        limit=limit,
    )
    return EndpointListResponse(items=[_build_response(e) for e in endpoints], total=total)


@router.get("/{endpoint_id}/executions", response_model=EndpointExecutionListResponse)
async def list_endpoint_executions(
    endpoint_id: str,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EndpointExecutionListResponse:
    """List execution history for a custom endpoint, newest first."""
    endpoint = await repo.get(endpoint_id)
    if endpoint is None or endpoint.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    from snackbase.infrastructure.persistence.repositories.endpoint_execution_repository import (
        EndpointExecutionRepository,
    )

    exec_repo = EndpointExecutionRepository(session)
    executions, total = await exec_repo.list_for_endpoint(endpoint_id, offset=offset, limit=limit)

    return EndpointExecutionListResponse(
        items=[EndpointExecutionResponse.model_validate(e) for e in executions],
        total=total,
    )


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
) -> EndpointResponse:
    """Retrieve a single custom endpoint by ID."""
    endpoint = await repo.get(endpoint_id)
    if endpoint is None or endpoint.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    return _build_response(endpoint)


@router.patch("/{endpoint_id}/toggle", response_model=EndpointResponse)
async def toggle_endpoint(
    endpoint_id: str,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EndpointResponse:
    """Toggle a custom endpoint's enabled/disabled state."""
    endpoint = await repo.get(endpoint_id)
    if endpoint is None or endpoint.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    endpoint.enabled = not endpoint.enabled
    await repo.update(endpoint)
    await session.commit()
    await session.refresh(endpoint)

    logger.info("Endpoint toggled", endpoint_id=endpoint_id, enabled=endpoint.enabled)
    return _build_response(endpoint)


@router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    data: EndpointUpdateRequest,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EndpointResponse:
    """Update a custom endpoint."""
    endpoint = await repo.get(endpoint_id)
    if endpoint is None or endpoint.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    # Check uniqueness if path or method is changing
    new_path = data.path if data.path is not None else endpoint.path
    new_method = data.method if data.method is not None else endpoint.method

    if (new_path != endpoint.path or new_method != endpoint.method) and await repo.exists_by_path_and_method(
        current_user.account_id, new_path, new_method, exclude_id=endpoint_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An endpoint with path '{new_path}' and method '{new_method}' "
                "already exists for this account"
            ),
        )

    if data.name is not None:
        endpoint.name = data.name
    if data.description is not None:
        endpoint.description = data.description
    if data.path is not None:
        endpoint.path = data.path
    if data.method is not None:
        endpoint.method = data.method
    if data.auth_required is not None:
        endpoint.auth_required = data.auth_required
    if data.condition is not None:
        endpoint.condition = data.condition if data.condition != "" else None
    if data.actions is not None:
        endpoint.actions = data.actions
    if data.response_template is not None:
        endpoint.response_template = data.response_template
    if data.enabled is not None:
        endpoint.enabled = data.enabled

    await repo.update(endpoint)
    await session.commit()
    await session.refresh(endpoint)

    logger.info("Endpoint updated", endpoint_id=endpoint_id)
    return _build_response(endpoint)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    current_user: AuthenticatedUser,
    repo: EndpointRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a custom endpoint."""
    endpoint = await repo.get(endpoint_id)
    if endpoint is None or endpoint.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    await repo.delete(endpoint_id)
    await session.commit()
    logger.info("Endpoint deleted", endpoint_id=endpoint_id)
