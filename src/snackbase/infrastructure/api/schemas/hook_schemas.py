"""Pydantic schemas for the hooks API (scheduled tasks + future event hooks)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HookCreateRequest(BaseModel):
    """Request body for creating a scheduled hook."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable name")
    description: str | None = Field(None, description="Optional description")
    cron: str = Field(..., description="5-field cron expression (e.g. '0 9 * * MON')")
    enabled: bool = Field(True, description="Whether the hook is active on creation")
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Actions to execute when the hook fires (populated in F8.1)",
    )


class HookUpdateRequest(BaseModel):
    """Request body for updating a scheduled hook (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    cron: str | None = Field(None, description="Updated cron expression")
    enabled: bool | None = None
    actions: list[dict[str, Any]] | None = None


class HookResponse(BaseModel):
    """Response schema for a single hook."""

    id: str
    account_id: str
    name: str
    description: str | None
    trigger: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    cron: str | None = Field(None, description="Cron expression extracted from trigger")
    cron_description: str | None = Field(None, description="Human-readable cron description")

    model_config = {"from_attributes": True}


class HookListResponse(BaseModel):
    """Paginated list of hooks."""

    items: list[HookResponse]
    total: int
