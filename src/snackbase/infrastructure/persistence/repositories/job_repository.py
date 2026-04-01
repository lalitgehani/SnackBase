"""Repository for background job queue database operations."""

from datetime import UTC, datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.job import JobModel


class JobRepository:
    """Repository for job queue database operations.

    Provides data access methods for the background job queue,
    including dialect-aware job pickup (SELECT FOR UPDATE SKIP LOCKED
    on PostgreSQL; atomic UPDATE claim on SQLite).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _is_postgresql(self) -> bool:
        """Check if the current database dialect is PostgreSQL."""
        from snackbase.core.config import get_settings

        settings = get_settings()
        return "postgresql" in settings.database_url

    async def create(self, job: JobModel) -> JobModel:
        """Persist a new job record."""
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: str) -> JobModel | None:
        """Get a job by ID."""
        result = await self.session.execute(
            select(JobModel).where(JobModel.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        status: str | None = None,
        queue: str | None = None,
        handler: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[JobModel], int]:
        """List jobs with optional filters and pagination.

        Returns:
            Tuple of (jobs, total_count).
        """
        conditions = []
        if status:
            conditions.append(JobModel.status == status)
        if queue:
            conditions.append(JobModel.queue == queue)
        if handler:
            conditions.append(JobModel.handler == handler)

        where_clause = and_(*conditions) if conditions else True

        count_result = await self.session.execute(
            select(func.count(JobModel.id)).where(where_clause)
        )
        total = count_result.scalar_one() or 0

        result = await self.session.execute(
            select(JobModel)
            .where(where_clause)
            .order_by(JobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all(), total

    async def get_stats(self) -> dict[str, int]:
        """Get job counts grouped by status.

        Returns:
            Dict mapping status → count for all known statuses.
        """
        result = await self.session.execute(
            select(JobModel.status, func.count(JobModel.id).label("count")).group_by(
                JobModel.status
            )
        )
        rows = result.all()
        # Initialize all statuses to 0 so callers always get all keys
        stats: dict[str, int] = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0,
            "dead": 0,
        }
        for row in rows:
            stats[row.status] = row.count
        return stats

    async def pick_next_job(self, queue_filter: str | None = None) -> JobModel | None:
        """Atomically pick and claim the next available job.

        Uses SELECT FOR UPDATE SKIP LOCKED on PostgreSQL for true concurrent
        worker support. Falls back to an atomic UPDATE claim on SQLite (which
        is a single-writer database, so concurrent processes are already
        serialized, but the rowcount check guards against concurrent asyncio tasks).

        Args:
            queue_filter: Only pick jobs from this queue (None = any queue).

        Returns:
            The claimed JobModel, or None if no job is available.
        """
        now = datetime.now(UTC)
        base_conditions = [
            JobModel.status.in_(["pending", "retrying"]),
            or_(JobModel.run_at.is_(None), JobModel.run_at <= now),
        ]
        if queue_filter:
            base_conditions.append(JobModel.queue == queue_filter)

        where_clause = and_(*base_conditions)

        if self._is_postgresql():
            # PostgreSQL: true SELECT FOR UPDATE SKIP LOCKED
            stmt = (
                select(JobModel)
                .where(where_clause)
                .order_by(JobModel.priority.asc(), JobModel.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            result = await self.session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                return None
            # Mark as running while still holding the row lock
            await self.session.execute(
                update(JobModel)
                .where(JobModel.id == job.id)
                .values(status="running", started_at=now)
            )
            await self.session.flush()
            return job
        else:
            # SQLite: SELECT then atomic UPDATE claim
            stmt = (
                select(JobModel)
                .where(where_clause)
                .order_by(JobModel.priority.asc(), JobModel.created_at.asc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                return None

            # Attempt atomic claim: UPDATE only succeeds if status hasn't changed
            update_result = await self.session.execute(
                update(JobModel)
                .where(
                    and_(
                        JobModel.id == job.id,
                        JobModel.status == job.status,
                    )
                )
                .values(status="running", started_at=now)
            )
            await self.session.flush()
            if update_result.rowcount == 0:
                # Another coroutine claimed it first
                return None
            return job

    async def mark_running(self, job_id: str) -> None:
        """Mark a job as running and set started_at.

        On PostgreSQL this is called after pick_next_job already set the status
        within the lock transaction (idempotent). On SQLite pick_next_job
        already performs the mark_running atomically.
        """
        await self.session.execute(
            update(JobModel)
            .where(JobModel.id == job_id)
            .values(status="running", started_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def mark_completed(self, job_id: str) -> None:
        """Mark a job as successfully completed."""
        await self.session.execute(
            update(JobModel)
            .where(JobModel.id == job_id)
            .values(status="completed", completed_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def mark_failed(
        self,
        job_id: str,
        error: str,
        next_run_at: datetime | None,
        new_status: str,
    ) -> None:
        """Mark a job as failed or dead, incrementing the attempt counter.

        Args:
            job_id: ID of the job to update.
            error: Error message to store (truncated to 5000 chars).
            next_run_at: When to retry (None for dead/permanent failure).
            new_status: Either "retrying" or "dead".
        """
        values: dict = {
            "status": new_status,
            "failed_at": datetime.now(UTC),
            "error_message": error[:5000] if error else None,
            "attempt_number": JobModel.attempt_number + 1,
        }
        if next_run_at is not None:
            values["run_at"] = next_run_at

        await self.session.execute(
            update(JobModel).where(JobModel.id == job_id).values(**values)
        )
        await self.session.flush()

    async def retry_job(self, job_id: str) -> bool:
        """Reset a dead or failed job back to pending for manual retry.

        Args:
            job_id: ID of the job to retry.

        Returns:
            True if the job was found and eligible for retry, False otherwise.
        """
        result = await self.session.execute(
            update(JobModel)
            .where(
                and_(
                    JobModel.id == job_id,
                    JobModel.status.in_(["dead", "failed"]),
                )
            )
            .values(
                status="pending",
                run_at=None,
                error_message=None,
                attempt_number=0,
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def reset_stale_jobs(self, timeout_seconds: int) -> int:
        """Reset jobs that have been running longer than the timeout back to pending.

        Called periodically by the worker to recover from crashed workers.

        Args:
            timeout_seconds: Jobs running longer than this are considered stale.

        Returns:
            Number of stale jobs reset.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        result = await self.session.execute(
            update(JobModel)
            .where(
                and_(
                    JobModel.status == "running",
                    JobModel.started_at <= cutoff,
                )
            )
            .values(status="pending", started_at=None)
        )
        await self.session.flush()
        return result.rowcount

    async def delete_completed_before(self, cutoff: datetime) -> int:
        """Delete completed jobs older than the cutoff for retention cleanup.

        Args:
            cutoff: Delete completed jobs with completed_at <= this datetime.

        Returns:
            Number of deleted jobs.
        """
        result = await self.session.execute(
            delete(JobModel).where(
                and_(
                    JobModel.status == "completed",
                    JobModel.completed_at <= cutoff,
                )
            )
        )
        await self.session.flush()
        return result.rowcount

    async def delete_by_id(self, job_id: str) -> bool:
        """Hard-delete a job by ID.

        Args:
            job_id: ID of the job to delete.

        Returns:
            True if deleted, False if not found.
        """
        job = await self.get_by_id(job_id)
        if job is None:
            return False
        await self.session.delete(job)
        await self.session.flush()
        return True
