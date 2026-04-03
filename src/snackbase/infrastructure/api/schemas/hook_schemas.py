"""Pydantic schemas for the hooks API.

Supports all three trigger types introduced in F8.1:
    - schedule: fires on a cron schedule (F7.3)
    - event:    fires when a data event occurs (F8.1)
    - manual:   fires only via explicit API call (F8.1)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Trigger type schemas (discriminated union on "type")
# ---------------------------------------------------------------------------


class ScheduleTriggerConfig(BaseModel):
    """Trigger that fires on a cron schedule."""

    type: Literal["schedule"]
    cron: str = Field(..., description="5-field cron expression (e.g. '0 9 * * MON')")


class EventTriggerConfig(BaseModel):
    """Trigger that fires when a platform event occurs."""

    type: Literal["event"]
    event: str = Field(
        ...,
        description=(
            "Event to listen for. Supported: records.create, records.update, "
            "records.delete, auth.login, auth.register"
        ),
    )
    collection: str | None = Field(
        None,
        description="Restrict to a specific collection (record events only). "
                    "Omit to listen on all collections.",
    )


class ManualTriggerConfig(BaseModel):
    """Trigger that only fires when called explicitly via the API."""

    type: Literal["manual"]


TriggerConfig = Annotated[
    Union[ScheduleTriggerConfig, EventTriggerConfig, ManualTriggerConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

# Valid event names for event-type triggers
VALID_EVENT_NAMES = {
    "records.create",
    "records.update",
    "records.delete",
    "auth.login",
    "auth.register",
}


class HookCreateRequest(BaseModel):
    """Request body for creating a hook (any trigger type)."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable name")
    description: str | None = Field(None, description="Optional description")
    trigger: TriggerConfig = Field(..., description="When this hook fires")
    condition: str | None = Field(
        None,
        description="Optional rule expression — hook only fires when this evaluates to True",
    )
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of actions to execute",
    )
    enabled: bool = Field(True, description="Whether the hook is active on creation")


class HookUpdateRequest(BaseModel):
    """Request body for updating a hook (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    trigger: TriggerConfig | None = Field(None, description="Updated trigger definition")
    condition: str | None = Field(None, description="Updated condition expression (pass '' to clear)")
    actions: list[dict[str, Any]] | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class HookResponse(BaseModel):
    """Response schema for a single hook."""

    id: str
    account_id: str
    name: str
    description: str | None
    trigger: dict[str, Any]
    condition: str | None
    actions: list[dict[str, Any]]
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    # Convenience fields for schedule-type hooks
    cron: str | None = Field(None, description="Cron expression (schedule triggers only)")
    cron_description: str | None = Field(None, description="Human-readable cron schedule")

    model_config = {"from_attributes": True}


class HookListResponse(BaseModel):
    """Paginated list of hooks."""

    items: list[HookResponse]
    total: int


# ---------------------------------------------------------------------------
# Execution history schemas
# ---------------------------------------------------------------------------


class HookExecutionResponse(BaseModel):
    """Response schema for a single hook execution record."""

    id: str
    hook_id: str
    trigger_type: str
    status: str
    actions_executed: int
    error_message: str | None
    duration_ms: int | None
    execution_context: dict[str, Any] | None
    executed_at: datetime

    model_config = {"from_attributes": True}


class HookExecutionListResponse(BaseModel):
    """Paginated list of hook executions."""

    items: list[HookExecutionResponse]
    total: int
