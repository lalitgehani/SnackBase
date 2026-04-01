"""API router for hook management (scheduled tasks).

Account-scoped CRUD endpoints for hooks. Currently supports schedule-type hooks
(F7.3 Cron Infrastructure). Event-type hooks will be added in F8.1.

Endpoints:
    POST   /                  Create a new scheduled hook
    GET    /                  List hooks for the account (filter by trigger_type)
    GET    /{hook_id}         Get a single hook
    PATCH  /{hook_id}         Update a hook
    DELETE /{hook_id}         Delete a hook
    PATCH  /{hook_id}/toggle  Toggle enabled/disabled
    POST   /{hook_id}/trigger Manually trigger (enqueue a job immediately)

Note: /{hook_id}/toggle and /{hook_id}/trigger must be registered before
/{hook_id} PUT/DELETE to avoid FastAPI matching literal strings as IDs.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.cron.parser import describe_cron, get_next_run, validate_cron
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.hook_schemas import (
    HookCreateRequest,
    HookListResponse,
    HookResponse,
    HookUpdateRequest,
)
from snackbase.infrastructure.persistence.models.hook import HookModel
from snackbase.infrastructure.persistence.repositories.hook_repository import HookRepository

router = APIRouter(tags=["Hooks"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def get_hook_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookRepository:
    """Dependency: create a HookRepository for the current request session."""
    return HookRepository(session)


HookRepo = Annotated[HookRepository, Depends(get_hook_repository)]


def _build_response(hook: HookModel) -> HookResponse:
    """Build a HookResponse from an ORM model, computing cron/description."""
    cron_expr: str | None = None
    cron_desc: str | None = None

    if isinstance(hook.trigger, dict) and hook.trigger.get("type") == "schedule":
        cron_expr = hook.trigger.get("cron")
        if cron_expr:
            cron_desc = describe_cron(cron_expr)

    return HookResponse(
        id=hook.id,
        account_id=hook.account_id,
        name=hook.name,
        description=hook.description,
        trigger=hook.trigger,
        actions=hook.actions or [],
        enabled=hook.enabled,
        last_run_at=hook.last_run_at,
        next_run_at=hook.next_run_at,
        created_at=hook.created_at,
        updated_at=hook.updated_at,
        created_by=hook.created_by,
        cron=cron_expr,
        cron_description=cron_desc,
    )


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=HookResponse)
async def create_hook(
    data: HookCreateRequest,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookResponse:
    """Create a new scheduled hook for the current account.

    The cron expression is validated and ``next_run_at`` is pre-calculated.
    """
    is_valid, err = validate_cron(data.cron)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid cron expression: {err}",
        )

    now = _now_naive()
    next_run = get_next_run(data.cron, now)

    hook = HookModel(
        account_id=current_user.account_id,
        name=data.name,
        description=data.description,
        trigger={"type": "schedule", "cron": data.cron},
        actions=data.actions,
        enabled=data.enabled,
        next_run_at=next_run if data.enabled else None,
        created_by=current_user.user_id,
    )

    await repo.create(hook)
    await session.commit()
    await session.refresh(hook)

    logger.info("Scheduled hook created", hook_id=hook.id, account_id=current_user.account_id)
    return _build_response(hook)


@router.get("", response_model=HookListResponse)
async def list_hooks(
    current_user: AuthenticatedUser,
    repo: HookRepo,
    trigger_type: str | None = Query(default=None, description="Filter by trigger type"),
    enabled: bool | None = Query(default=None, description="Filter by enabled status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> HookListResponse:
    """List hooks for the current account with optional filters."""
    hooks, total = await repo.list_for_account(
        account_id=current_user.account_id,
        trigger_type=trigger_type,
        enabled=enabled,
        offset=offset,
        limit=limit,
    )
    return HookListResponse(
        items=[_build_response(h) for h in hooks],
        total=total,
    )


@router.get("/{hook_id}", response_model=HookResponse)
async def get_hook(
    hook_id: str,
    current_user: AuthenticatedUser,
    repo: HookRepo,
) -> HookResponse:
    """Retrieve a single hook by ID."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")
    return _build_response(hook)


@router.patch("/{hook_id}/toggle", response_model=HookResponse)
async def toggle_hook(
    hook_id: str,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookResponse:
    """Toggle a hook's enabled/disabled state.

    When enabling, ``next_run_at`` is recalculated from now.
    When disabling, ``next_run_at`` is cleared.
    """
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    hook.enabled = not hook.enabled

    if hook.enabled:
        cron = hook.trigger.get("cron", "") if isinstance(hook.trigger, dict) else ""
        if cron:
            now = _now_naive()
            hook.next_run_at = get_next_run(cron, now)
    else:
        hook.next_run_at = None

    await repo.update(hook)
    await session.commit()
    await session.refresh(hook)

    logger.info("Hook toggled", hook_id=hook_id, enabled=hook.enabled)
    return _build_response(hook)


@router.post("/{hook_id}/trigger", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def trigger_hook(
    hook_id: str,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Manually trigger a hook by enqueuing a job immediately.

    The hook does not need to be enabled to be triggered manually.
    """
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    from snackbase.infrastructure.persistence.models.job import JobModel
    from snackbase.infrastructure.persistence.repositories.job_repository import JobRepository

    job_repo = JobRepository(session)
    job = JobModel(
        handler="scheduled_hook",
        payload={
            "hook_id": hook.id,
            "hook_name": hook.name,
            "actions": hook.actions or [],
            "manual": True,
        },
        queue="scheduled",
        account_id=hook.account_id,
    )
    await job_repo.create(job)
    await session.commit()

    logger.info("Hook manually triggered", hook_id=hook_id, job_id=job.id)
    return {"job_id": job.id, "message": "Job enqueued successfully"}


@router.patch("/{hook_id}", response_model=HookResponse)
async def update_hook(
    hook_id: str,
    data: HookUpdateRequest,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookResponse:
    """Update a scheduled hook."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    if data.name is not None:
        hook.name = data.name
    if data.description is not None:
        hook.description = data.description
    if data.actions is not None:
        hook.actions = data.actions

    cron_changed = False
    if data.cron is not None:
        is_valid, err = validate_cron(data.cron)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid cron expression: {err}",
            )
        hook.trigger = {"type": "schedule", "cron": data.cron}
        cron_changed = True

    if data.enabled is not None:
        hook.enabled = data.enabled

    # Recalculate next_run_at if cron changed or enabled state changed
    if hook.enabled:
        cron = hook.trigger.get("cron", "") if isinstance(hook.trigger, dict) else ""
        if cron and (cron_changed or data.enabled is not None):
            hook.next_run_at = get_next_run(cron, _now_naive())
    else:
        hook.next_run_at = None

    await repo.update(hook)
    await session.commit()
    await session.refresh(hook)

    logger.info("Hook updated", hook_id=hook_id)
    return _build_response(hook)


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hook(
    hook_id: str,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a scheduled hook."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    await repo.delete(hook_id)
    await session.commit()
    logger.info("Hook deleted", hook_id=hook_id)
