"""API router for hook management (F7.3 + F8.1).

Account-scoped CRUD endpoints for hooks. Supports all three trigger types:
    - schedule: cron-based triggers (F7.3)
    - event:    fires on data events (F8.1)
    - manual:   fired only via explicit API call (F8.1)

Endpoints:
    POST   /                      Create a new hook
    GET    /                      List hooks for the account
    GET    /{hook_id}             Get a single hook
    PATCH  /{hook_id}             Update a hook
    DELETE /{hook_id}             Delete a hook
    PATCH  /{hook_id}/toggle      Toggle enabled/disabled
    POST   /{hook_id}/trigger     Manually trigger a hook
    GET    /{hook_id}/executions  List execution history for a hook

Note: /{hook_id}/toggle, /{hook_id}/trigger, and /{hook_id}/executions must be
registered before /{hook_id} PATCH/DELETE to avoid FastAPI matching the literal
path segment as a hook ID.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.cron.parser import describe_cron, get_next_run, validate_cron
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.hook_schemas import (
    HookCreateRequest,
    HookExecutionListResponse,
    HookExecutionResponse,
    HookListResponse,
    HookResponse,
    HookUpdateRequest,
    VALID_EVENT_NAMES,
)
from snackbase.infrastructure.persistence.models.hook import HookModel
from snackbase.infrastructure.persistence.repositories.hook_repository import HookRepository

router = APIRouter(tags=["Hooks"])
logger = get_logger(__name__)

# Default maximum hooks per account (can be overridden by settings)
_DEFAULT_MAX_HOOKS = 50


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def get_hook_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookRepository:
    return HookRepository(session)


HookRepo = Annotated[HookRepository, Depends(get_hook_repository)]


def _build_response(hook: HookModel) -> HookResponse:
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
        condition=hook.condition,
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


def _get_max_hooks(request: Request) -> int:
    """Read max hooks limit from app settings if available."""
    try:
        from snackbase.core.config import get_settings
        settings = get_settings()
        return getattr(settings, "max_hooks_per_account", _DEFAULT_MAX_HOOKS)
    except Exception:
        return _DEFAULT_MAX_HOOKS


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=HookResponse)
async def create_hook(
    data: HookCreateRequest,
    request: Request,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookResponse:
    """Create a new hook for the current account.

    Supports schedule, event, and manual trigger types. Returns 422 for invalid
    cron expressions or unrecognised event names. Returns 409 when the account
    has reached the maximum hook limit.
    """
    max_hooks = _get_max_hooks(request)
    current_count = await repo.count_hooks_for_account(current_user.account_id)
    if current_count >= max_hooks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account has reached the maximum of {max_hooks} hooks",
        )

    trigger_dict: dict
    next_run: datetime | None = None

    trigger = data.trigger

    if trigger.type == "schedule":
        is_valid, err = validate_cron(trigger.cron)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid cron expression: {err}",
            )
        now = _now_naive()
        next_run = get_next_run(trigger.cron, now) if data.enabled else None
        trigger_dict = {"type": "schedule", "cron": trigger.cron}

    elif trigger.type == "event":
        if trigger.event not in VALID_EVENT_NAMES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Unknown event '{trigger.event}'. "
                    f"Supported: {', '.join(sorted(VALID_EVENT_NAMES))}"
                ),
            )
        trigger_dict = {"type": "event", "event": trigger.event}
        if trigger.collection:
            trigger_dict["collection"] = trigger.collection

    else:  # manual
        trigger_dict = {"type": "manual"}

    hook = HookModel(
        account_id=current_user.account_id,
        name=data.name,
        description=data.description,
        trigger=trigger_dict,
        condition=data.condition,
        actions=data.actions,
        enabled=data.enabled,
        next_run_at=next_run,
        created_by=current_user.user_id,
    )

    await repo.create(hook)
    await session.commit()
    await session.refresh(hook)

    logger.info(
        "Hook created",
        hook_id=hook.id,
        trigger_type=trigger.type,
        account_id=current_user.account_id,
    )
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
    return HookListResponse(items=[_build_response(h) for h in hooks], total=total)


@router.get("/{hook_id}/executions", response_model=HookExecutionListResponse)
async def list_hook_executions(
    hook_id: str,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> HookExecutionListResponse:
    """List execution history for a hook, newest first."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    from snackbase.infrastructure.persistence.repositories.hook_execution_repository import (
        HookExecutionRepository,
    )

    exec_repo = HookExecutionRepository(session)
    executions, total = await exec_repo.list_for_hook(hook_id, offset=offset, limit=limit)

    return HookExecutionListResponse(
        items=[HookExecutionResponse.model_validate(e) for e in executions],
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

    For schedule-type hooks, ``next_run_at`` is recalculated when re-enabling.
    """
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    hook.enabled = not hook.enabled

    if hook.enabled and isinstance(hook.trigger, dict) and hook.trigger.get("type") == "schedule":
        cron = hook.trigger.get("cron", "")
        if cron:
            hook.next_run_at = get_next_run(cron, _now_naive())
    elif not hook.enabled:
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
    """Manually trigger a hook.

    For schedule-type hooks a job is enqueued (existing behaviour).
    For event and manual hooks the actions are executed inline and an execution
    record is written. The hook does not need to be enabled.
    """
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    trigger_type = hook.trigger.get("type") if isinstance(hook.trigger, dict) else "manual"

    if trigger_type == "schedule":
        # Legacy: enqueue as a job (consistent with F7.3 scheduler behaviour)
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

        logger.info("Scheduled hook manually enqueued", hook_id=hook_id, job_id=job.id)
        return {"message": "Job enqueued successfully", "job_id": job.id}

    # For event and manual hooks: execute inline
    from snackbase.domain.entities.hook_context import HookContext
    from snackbase.infrastructure.persistence.database import get_db_manager

    db_manager = get_db_manager()
    ctx = HookContext(app=None, account_id=current_user.account_id)

    from snackbase.infrastructure.hooks.api_defined_hook import execute_hook_manually

    actions_executed, error_message = await execute_hook_manually(
        hook=hook,
        context=ctx,
        session_factory=db_manager.session,
    )

    status_str = "success"
    if error_message:
        status_str = "partial" if actions_executed > 0 else "failed"

    logger.info(
        "Hook manually triggered",
        hook_id=hook_id,
        actions_executed=actions_executed,
        status=status_str,
    )
    return {
        "message": "Hook executed",
        "status": status_str,
        "actions_executed": actions_executed,
        "error": error_message,
    }


@router.patch("/{hook_id}", response_model=HookResponse)
async def update_hook(
    hook_id: str,
    data: HookUpdateRequest,
    current_user: AuthenticatedUser,
    repo: HookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HookResponse:
    """Update a hook."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    if data.name is not None:
        hook.name = data.name
    if data.description is not None:
        hook.description = data.description
    if data.actions is not None:
        hook.actions = data.actions
    if data.condition is not None:
        hook.condition = data.condition if data.condition != "" else None
    if data.enabled is not None:
        hook.enabled = data.enabled

    trigger_changed = False
    if data.trigger is not None:
        trigger = data.trigger

        if trigger.type == "schedule":
            is_valid, err = validate_cron(trigger.cron)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid cron expression: {err}",
                )
            hook.trigger = {"type": "schedule", "cron": trigger.cron}

        elif trigger.type == "event":
            if trigger.event not in VALID_EVENT_NAMES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Unknown event '{trigger.event}'. "
                        f"Supported: {', '.join(sorted(VALID_EVENT_NAMES))}"
                    ),
                )
            new_trigger: dict = {"type": "event", "event": trigger.event}
            if trigger.collection:
                new_trigger["collection"] = trigger.collection
            hook.trigger = new_trigger

        else:  # manual
            hook.trigger = {"type": "manual"}

        trigger_changed = True

    # Recalculate next_run_at for schedule-type hooks when trigger or enabled changes
    if isinstance(hook.trigger, dict) and hook.trigger.get("type") == "schedule":
        cron = hook.trigger.get("cron", "")
        if hook.enabled and cron and (trigger_changed or data.enabled is not None):
            hook.next_run_at = get_next_run(cron, _now_naive())
        elif not hook.enabled:
            hook.next_run_at = None
    else:
        # Non-schedule hooks don't use next_run_at
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
    """Delete a hook."""
    hook = await repo.get(hook_id)
    if hook is None or hook.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    await repo.delete(hook_id)
    await session.commit()
    logger.info("Hook deleted", hook_id=hook_id)
