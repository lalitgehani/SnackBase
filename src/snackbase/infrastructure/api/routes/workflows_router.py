"""API router for the F8.3 Workflow Engine.

Provides account-scoped CRUD for workflow definitions, triggering, instance
management, and a public webhook dispatcher endpoint.

Endpoints (all under /api/v1/ prefix):
    POST   /workflows                           Create workflow
    GET    /workflows                           List workflows
    GET    /workflows/{id}                      Get workflow
    PUT    /workflows/{id}                      Update workflow
    DELETE /workflows/{id}                      Delete workflow (204)
    PATCH  /workflows/{id}/toggle               Toggle enabled/disabled
    POST   /workflows/{id}/trigger              Manually trigger a new instance
    GET    /workflows/{id}/instances            List instances for a workflow
    GET    /workflow-instances/{id}             Get instance detail (with step logs)
    POST   /workflow-instances/{id}/cancel      Cancel a running/waiting instance
    POST   /workflow-instances/{id}/resume      Resume a failed instance
    POST   /workflow-webhooks/{token}           Webhook trigger (no auth required)

Note: /{id}/toggle, /{id}/trigger, /{id}/instances must be registered before
/{id} PUT/DELETE to avoid FastAPI matching literal path segments as an ID.
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Annotated, Any, Set

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.cron.parser import validate_cron
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.workflow_schemas import (
    TriggerWorkflowResponse,
    WorkflowCreateRequest,
    WorkflowInstanceDetailResponse,
    WorkflowInstanceListResponse,
    WorkflowInstanceResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowStepLogResponse,
    WorkflowUpdateRequest,
    VALID_WORKFLOW_EVENTS,
)
from snackbase.infrastructure.persistence.models.workflow import WorkflowModel
from snackbase.infrastructure.persistence.models.workflow_instance import WorkflowInstanceModel
from snackbase.infrastructure.persistence.repositories.workflow_instance_repository import (
    WorkflowInstanceRepository,
)
from snackbase.infrastructure.persistence.repositories.workflow_repository import (
    WorkflowRepository,
)
from snackbase.infrastructure.persistence.repositories.workflow_step_log_repository import (
    WorkflowStepLogRepository,
)

logger = get_logger(__name__)

_DEFAULT_MAX_WORKFLOWS = 50

# Keep references to prevent background tasks from being GC'd
_background_tasks: Set[asyncio.Task] = set()

# ---------------------------------------------------------------------------
# Routers — two separate routers so they can be mounted at different prefixes
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Workflows"])
webhook_router = APIRouter(tags=["Workflows"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def get_workflow_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowRepository:
    return WorkflowRepository(session)


def get_instance_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowInstanceRepository:
    return WorkflowInstanceRepository(session)


WorkflowRepo = Annotated[WorkflowRepository, Depends(get_workflow_repository)]
InstanceRepo = Annotated[WorkflowInstanceRepository, Depends(get_instance_repository)]


def _get_max_workflows(request: Request) -> int:
    try:
        from snackbase.core.config import get_settings

        settings = get_settings()
        return getattr(settings, "max_workflows_per_account", _DEFAULT_MAX_WORKFLOWS)
    except Exception:
        return _DEFAULT_MAX_WORKFLOWS


def _build_workflow_response(wf: WorkflowModel) -> WorkflowResponse:
    return WorkflowResponse(
        id=wf.id,
        account_id=wf.account_id,
        name=wf.name,
        description=wf.description,
        trigger_type=wf.trigger_type,
        trigger_config=wf.trigger_config or {},
        steps=wf.steps or [],
        enabled=wf.enabled,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        created_by=wf.created_by,
    )


def _build_instance_response(inst: WorkflowInstanceModel) -> WorkflowInstanceResponse:
    return WorkflowInstanceResponse(
        id=inst.id,
        workflow_id=inst.workflow_id,
        account_id=inst.account_id,
        status=inst.status,
        current_step=inst.current_step,
        context=inst.context or {},
        started_at=inst.started_at,
        completed_at=inst.completed_at,
        error_message=inst.error_message,
        resume_job_id=inst.resume_job_id,
    )


def _validate_trigger(trigger_dict: dict[str, Any]) -> None:
    """Validate trigger config; raises HTTPException on invalid input."""
    t_type = trigger_dict.get("type")
    if t_type == "schedule":
        cron = trigger_dict.get("cron", "")
        is_valid, err = validate_cron(cron)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid cron expression: {err}",
            )
    elif t_type == "event":
        event = trigger_dict.get("event", "")
        if event not in VALID_WORKFLOW_EVENTS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Unknown event '{event}'. "
                    f"Supported: {', '.join(sorted(VALID_WORKFLOW_EVENTS))}"
                ),
            )


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------


@router.post("/workflows", status_code=status.HTTP_201_CREATED, response_model=WorkflowResponse)
async def create_workflow(
    data: WorkflowCreateRequest,
    request: Request,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowResponse:
    """Create a new workflow for the current account."""
    max_wf = _get_max_workflows(request)
    current_count = await repo.count_for_account(current_user.account_id)
    if current_count >= max_wf:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account has reached the maximum of {max_wf} workflows",
        )

    trigger_dict = data.trigger.model_dump()
    _validate_trigger(trigger_dict)

    # Generate webhook token if needed
    if trigger_dict.get("type") == "webhook":
        trigger_dict["token"] = secrets.token_urlsafe(32)

    wf = WorkflowModel(
        account_id=current_user.account_id,
        name=data.name,
        description=data.description,
        trigger_type=trigger_dict["type"],
        trigger_config=trigger_dict,
        steps=data.steps,
        enabled=data.enabled,
        created_by=current_user.user_id,
    )
    await repo.create(wf)
    await session.commit()
    await session.refresh(wf)

    logger.info(
        "Workflow created",
        workflow_id=wf.id,
        trigger_type=wf.trigger_type,
        account_id=current_user.account_id,
    )
    return _build_workflow_response(wf)


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    trigger_type: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WorkflowListResponse:
    """List workflows for the current account."""
    workflows, total = await repo.list_for_account(
        account_id=current_user.account_id,
        trigger_type=trigger_type,
        enabled=enabled,
        offset=offset,
        limit=limit,
    )
    return WorkflowListResponse(
        items=[_build_workflow_response(wf) for wf in workflows],
        total=total,
    )


@router.get("/workflows/{workflow_id}/instances", response_model=WorkflowInstanceListResponse)
async def list_workflow_instances(
    workflow_id: str,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    instance_repo: InstanceRepo,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WorkflowInstanceListResponse:
    """List instances for a workflow, newest first."""
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    instances, total = await instance_repo.list_for_workflow(
        workflow_id=workflow_id,
        account_id=current_user.account_id,
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    return WorkflowInstanceListResponse(
        items=[_build_instance_response(i) for i in instances],
        total=total,
    )


@router.post(
    "/workflows/{workflow_id}/trigger",
    response_model=TriggerWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_workflow(
    workflow_id: str,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    instance_repo: InstanceRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    body: dict[str, Any] | None = None,
) -> TriggerWorkflowResponse:
    """Manually trigger a workflow instance.

    Works for any trigger type. Accepts an optional JSON body that becomes
    the trigger context data available via ``{{trigger.*}}`` in step configs.
    """
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    trigger_data: dict[str, Any] = body or {}
    instance = WorkflowInstanceModel(
        workflow_id=wf.id,
        account_id=current_user.account_id,
        status="pending",
        context={"trigger": {**trigger_data, "_source": "manual"}, "steps": {}},
        started_at=datetime.now(UTC),
    )
    await instance_repo.create(instance)
    await session.commit()
    instance_id = instance.id

    # Run in background so the API returns immediately
    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.workflows.workflow_executor import run_instance

    db_manager = get_db_manager()

    task = asyncio.create_task(run_instance(instance_id, db_manager.session))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info(
        "Workflow manually triggered",
        workflow_id=workflow_id,
        instance_id=instance_id,
        account_id=current_user.account_id,
    )
    return TriggerWorkflowResponse(
        message="Workflow instance started",
        instance_id=instance_id,
    )


@router.patch(
    "/workflows/{workflow_id}/toggle",
    response_model=WorkflowResponse,
)
async def toggle_workflow(
    workflow_id: str,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowResponse:
    """Toggle a workflow's enabled/disabled state."""
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    wf.enabled = not wf.enabled
    await repo.update(wf)
    await session.commit()
    await session.refresh(wf)

    logger.info("Workflow toggled", workflow_id=workflow_id, enabled=wf.enabled)
    return _build_workflow_response(wf)


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
) -> WorkflowResponse:
    """Get a single workflow by ID."""
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return _build_workflow_response(wf)


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdateRequest,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowResponse:
    """Update a workflow definition."""
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if data.name is not None:
        wf.name = data.name
    if data.description is not None:
        wf.description = data.description
    if data.steps is not None:
        wf.steps = data.steps
    if data.enabled is not None:
        wf.enabled = data.enabled

    if data.trigger is not None:
        trigger_dict = data.trigger.model_dump()
        _validate_trigger(trigger_dict)

        if trigger_dict.get("type") == "webhook":
            # Preserve existing token; generate only if switching to webhook
            existing_token = (wf.trigger_config or {}).get("token")
            trigger_dict["token"] = existing_token or secrets.token_urlsafe(32)

        wf.trigger_type = trigger_dict["type"]
        wf.trigger_config = trigger_dict

    await repo.update(wf)
    await session.commit()
    await session.refresh(wf)

    logger.info("Workflow updated", workflow_id=workflow_id)
    return _build_workflow_response(wf)


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    current_user: AuthenticatedUser,
    repo: WorkflowRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a workflow and all its instances."""
    wf = await repo.get(workflow_id)
    if wf is None or wf.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    await repo.delete(workflow_id)
    await session.commit()
    logger.info("Workflow deleted", workflow_id=workflow_id)


# ---------------------------------------------------------------------------
# Instance management (mounted under /workflow-instances prefix)
# ---------------------------------------------------------------------------


@router.get(
    "/workflow-instances/{instance_id}",
    response_model=WorkflowInstanceDetailResponse,
)
async def get_instance(
    instance_id: str,
    current_user: AuthenticatedUser,
    instance_repo: InstanceRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowInstanceDetailResponse:
    """Get a workflow instance with its step logs."""
    inst = await instance_repo.get(instance_id)
    if inst is None or inst.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow instance not found"
        )

    log_repo = WorkflowStepLogRepository(session)
    logs, _ = await log_repo.list_for_instance(instance_id)

    return WorkflowInstanceDetailResponse(
        **_build_instance_response(inst).model_dump(),
        step_logs=[WorkflowStepLogResponse.model_validate(log) for log in logs],
    )


@router.post(
    "/workflow-instances/{instance_id}/cancel",
    response_model=WorkflowInstanceResponse,
)
async def cancel_instance(
    instance_id: str,
    current_user: AuthenticatedUser,
    instance_repo: InstanceRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowInstanceResponse:
    """Cancel a running or waiting workflow instance."""
    inst = await instance_repo.get(instance_id)
    if inst is None or inst.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow instance not found"
        )
    if inst.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Instance is already in '{inst.status}' state",
        )

    inst.status = "cancelled"
    inst.completed_at = datetime.now(UTC)
    await instance_repo.update(inst)
    await session.commit()
    await session.refresh(inst)

    logger.info("Workflow instance cancelled", instance_id=instance_id)
    return _build_instance_response(inst)


@router.post(
    "/workflow-instances/{instance_id}/resume",
    response_model=TriggerWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_instance_endpoint(
    instance_id: str,
    current_user: AuthenticatedUser,
    instance_repo: InstanceRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TriggerWorkflowResponse:
    """Resume a failed workflow instance from its last step."""
    inst = await instance_repo.get(instance_id)
    if inst is None or inst.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow instance not found"
        )
    if inst.status not in ("failed", "waiting"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only failed or waiting instances can be resumed (current: {inst.status!r})",
        )

    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.workflows.workflow_executor import resume_instance

    db_manager = get_db_manager()
    task = asyncio.create_task(
        resume_instance(instance_id, inst.current_step, db_manager.session)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info("Workflow instance resume requested", instance_id=instance_id)
    return TriggerWorkflowResponse(
        message="Workflow instance resume started",
        instance_id=instance_id,
    )


# ---------------------------------------------------------------------------
# Webhook trigger (no auth — uses secret token)
# ---------------------------------------------------------------------------


@webhook_router.post("/workflow-webhooks/{token}", status_code=status.HTTP_202_ACCEPTED)
async def workflow_webhook_trigger(
    token: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Trigger a webhook-type workflow via its secret token.

    The request body (JSON, if any) is passed as the trigger context.
    Returns 404 if no matching enabled workflow is found for the token.
    """
    wf_repo = WorkflowRepository(session)
    wf = await wf_repo.get_by_webhook_token(token)
    if wf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enabled workflow found for this webhook token",
        )

    # Parse body (optional)
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {"data": body}
    except Exception:
        body = {}

    instance_repo = WorkflowInstanceRepository(session)
    inst = WorkflowInstanceModel(
        workflow_id=wf.id,
        account_id=wf.account_id,
        status="pending",
        context={"trigger": {**body, "_source": "webhook"}, "steps": {}},
        started_at=datetime.now(UTC),
    )
    await instance_repo.create(inst)
    await session.commit()
    instance_id = inst.id

    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.workflows.workflow_executor import run_instance

    db_manager = get_db_manager()
    task = asyncio.create_task(run_instance(instance_id, db_manager.session))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info(
        "Workflow webhook triggered",
        workflow_id=wf.id,
        instance_id=instance_id,
    )
    return {"message": "Workflow instance started", "instance_id": instance_id}
