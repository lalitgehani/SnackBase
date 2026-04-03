"""Pydantic schemas for F8.3 Workflow Engine API.

Provides discriminated unions for trigger configs and step configs so the
API can validate polymorphic JSON with clear error messages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Trigger config schemas (discriminated on ``type``)
# ---------------------------------------------------------------------------

VALID_WORKFLOW_EVENTS = {
    "records.create",
    "records.update",
    "records.delete",
    "auth.login",
    "auth.register",
}


class EventTriggerConfig(BaseModel):
    type: Literal["event"]
    event: str = Field(..., description="Event name, e.g. 'records.create'")
    collection: str | None = Field(None, description="Restrict to a specific collection")
    condition: str | None = Field(None, description="Optional filter expression")


class ScheduleTriggerConfig(BaseModel):
    type: Literal["schedule"]
    cron: str = Field(..., description="5-field cron expression, e.g. '0 9 * * MON'")


class ManualTriggerConfig(BaseModel):
    type: Literal["manual"]


class WebhookTriggerConfig(BaseModel):
    type: Literal["webhook"]
    # ``token`` is server-generated; clients cannot supply it on create
    token: str | None = Field(None, description="Server-generated webhook token (read-only)")


TriggerConfig = Annotated[
    Union[
        EventTriggerConfig,
        ScheduleTriggerConfig,
        ManualTriggerConfig,
        WebhookTriggerConfig,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Step config schemas (discriminated on ``type``)
# ---------------------------------------------------------------------------


class ActionStep(BaseModel):
    type: Literal["action"]
    name: str = Field(..., description="Unique step name within the workflow")
    action_type: str = Field(
        ...,
        description=(
            "Action type: send_webhook | send_email | create_record | "
            "update_record | delete_record | enqueue_job"
        ),
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Action configuration (same schema as F8.1 hook actions)",
    )
    next: str | None = Field(None, description="Name of next step; None = workflow ends")


class ConditionStep(BaseModel):
    type: Literal["condition"]
    name: str
    expression: str = Field(..., description="Rule expression to evaluate")
    on_true: str | None = Field(None, description="Next step name if expression is true")
    on_false: str | None = Field(None, description="Next step name if expression is false")


class WaitDelayStep(BaseModel):
    type: Literal["wait_delay"]
    name: str
    duration: str = Field(
        ...,
        description="Pause duration, e.g. '5m', '2h', '1d'",
        examples=["5m", "30m", "2h", "1d"],
    )
    next: str | None = Field(None, description="Step to execute after the delay")


class WaitConditionStep(BaseModel):
    type: Literal["wait_condition"]
    name: str
    expression: str = Field(..., description="Poll until this expression is true")
    poll_interval: str = Field("1m", description="How often to check, e.g. '1m'")
    timeout: str = Field("24h", description="Give up after this duration")
    next: str | None = None


class WaitEventStep(BaseModel):
    type: Literal["wait_event"]
    name: str
    event: str = Field(..., description="Event to wait for, e.g. 'records.update'")
    collection: str | None = None
    condition: str | None = None
    timeout: str = Field("24h", description="Give up after this duration")
    next: str | None = None


class LoopStep(BaseModel):
    type: Literal["loop"]
    name: str
    items: str = Field(
        ...,
        description="Template expression resolving to a list, e.g. '{{trigger.records}}'",
    )
    step: str = Field(..., description="Name of the step to execute for each item")
    next: str | None = None


class ParallelStep(BaseModel):
    type: Literal["parallel"]
    name: str
    branches: list[list[str]] = Field(
        ...,
        description="Each inner list is an ordered sequence of step names to run in parallel",
    )
    next: str | None = None


StepConfig = Annotated[
    Union[
        ActionStep,
        ConditionStep,
        WaitDelayStep,
        WaitConditionStep,
        WaitEventStep,
        LoopStep,
        ParallelStep,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Workflow CRUD schemas
# ---------------------------------------------------------------------------


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger: TriggerConfig
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of step definition dicts",
    )
    enabled: bool = Field(True)


class WorkflowUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    trigger: TriggerConfig | None = None
    steps: list[dict[str, Any]] | None = None
    enabled: bool | None = None


class WorkflowResponse(BaseModel):
    id: str
    account_id: str
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict[str, Any]
    steps: list[dict[str, Any]]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = {"from_attributes": True}


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


# ---------------------------------------------------------------------------
# Workflow instance schemas
# ---------------------------------------------------------------------------


class WorkflowInstanceResponse(BaseModel):
    id: str
    workflow_id: str
    account_id: str
    status: str
    current_step: str | None
    context: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    resume_job_id: str | None

    model_config = {"from_attributes": True}


class WorkflowInstanceListResponse(BaseModel):
    items: list[WorkflowInstanceResponse]
    total: int


# ---------------------------------------------------------------------------
# Workflow step log schemas
# ---------------------------------------------------------------------------


class WorkflowStepLogResponse(BaseModel):
    id: str
    instance_id: str
    workflow_id: str
    account_id: str
    step_name: str
    step_type: str
    status: str
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowInstanceDetailResponse(WorkflowInstanceResponse):
    """Instance detail with embedded step logs."""
    step_logs: list[WorkflowStepLogResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Trigger response
# ---------------------------------------------------------------------------


class TriggerWorkflowResponse(BaseModel):
    message: str
    instance_id: str
