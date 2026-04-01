"""Admin API routes for the background job queue.

All endpoints require superadmin access. Provides:
- GET /  — list jobs with optional filters
- GET /stats — aggregate counts by status
- POST /{id}/retry — manually retry a dead/failed job
- DELETE /{id} — cancel a pending job

Note: /stats must be registered before /{id} to prevent FastAPI from
matching the literal string "stats" as a job ID path parameter.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser, get_db_session
from snackbase.infrastructure.api.schemas.job_schemas import (
    JobListResponse,
    JobResponse,
    JobStatsResponse,
)
from snackbase.infrastructure.persistence.repositories.job_repository import JobRepository

router = APIRouter(tags=["Jobs"])

logger = get_logger(__name__)


def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobRepository:
    """Dependency: create a JobRepository for the current request session."""
    return JobRepository(session)


JobRepo = Annotated[JobRepository, Depends(get_job_repository)]


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    _: SuperadminUser,
    repo: JobRepo,
) -> JobStatsResponse:
    """Get aggregate job counts by status.

    Returns counts for all statuses (pending, running, completed, failed,
    retrying, dead) and computed metrics (avg_duration_seconds, failure_rate).
    Counts are live snapshots from the database.
    """
    stats = await repo.get_stats()

    # Compute failure rate: (failed + dead) / total jobs that have finished or failed
    total_terminal = stats.get("completed", 0) + stats.get("failed", 0) + stats.get("dead", 0)
    failure_count = stats.get("failed", 0) + stats.get("dead", 0)
    failure_rate = (failure_count / total_terminal) if total_terminal > 0 else None

    return JobStatsResponse(
        pending=stats.get("pending", 0),
        running=stats.get("running", 0),
        completed=stats.get("completed", 0),
        failed=stats.get("failed", 0),
        retrying=stats.get("retrying", 0),
        dead=stats.get("dead", 0),
        avg_duration_seconds=None,  # Future: compute from started_at/completed_at
        failure_rate=failure_rate,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    _: SuperadminUser,
    repo: JobRepo,
    status_filter: str | None = Query(default=None, alias="status"),
    queue: str | None = Query(default=None),
    handler: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    """List background jobs with optional filters and pagination.

    Args:
        status_filter: Filter by job status (pending, running, completed, etc.).
        queue: Filter by queue name.
        handler: Filter by handler identifier.
        limit: Maximum records to return (1-200, default 50).
        offset: Records to skip for pagination (default 0).

    Returns:
        Paginated list of jobs with total count.
    """
    jobs, total = await repo.list_jobs(
        status=status_filter,
        queue=queue,
        handler=handler,
        limit=limit,
        offset=offset,
    )
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
    )


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    _: SuperadminUser,
    repo: JobRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobResponse:
    """Manually retry a dead or failed job.

    Resets the job's status to pending, clears the error message,
    and resets the attempt counter. The job will be picked up by
    the worker on the next poll cycle.

    Args:
        job_id: ID of the job to retry.

    Raises:
        404: Job not found.
        400: Job is not in dead or failed status.
    """
    job = await repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    if job.status not in ("dead", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is in status '{job.status}'; only dead or failed jobs can be retried",
        )

    retried = await repo.retry_job(job_id)
    if not retried:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retry job",
        )
    await session.commit()

    # Re-fetch to return updated state
    updated_job = await repo.get_by_id(job_id)
    if updated_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found after retry",
        )

    logger.info("Job manually retried", job_id=job_id)
    return JobResponse.model_validate(updated_job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: str,
    _: SuperadminUser,
    repo: JobRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Cancel and delete a pending job.

    Only jobs in 'pending' status can be cancelled. Running, completed,
    failed, retrying, and dead jobs cannot be cancelled.

    Args:
        job_id: ID of the job to cancel.

    Raises:
        404: Job not found.
        400: Job is not in pending status.
    """
    job = await repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    if job.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is in status '{job.status}'; only pending jobs can be cancelled",
        )

    await repo.delete_by_id(job_id)
    await session.commit()
    logger.info("Job cancelled", job_id=job_id)
