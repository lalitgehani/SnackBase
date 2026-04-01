"""Pydantic schemas for background job queue API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    """Response schema for a single job record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    queue: str
    handler: str
    payload: dict[str, Any]
    status: str
    priority: int
    run_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    attempt_number: int
    max_retries: int
    retry_delay_seconds: int
    created_at: datetime
    created_by: str | None
    account_id: str | None


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    items: list[JobResponse]
    total: int


class JobStatsResponse(BaseModel):
    """Aggregate job statistics grouped by status."""

    pending: int
    running: int
    completed: int
    failed: int
    retrying: int
    dead: int
    avg_duration_seconds: float | None
    failure_rate: float | None
