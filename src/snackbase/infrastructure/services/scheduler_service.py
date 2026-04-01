"""Cron scheduler service: polls schedule-type hooks and enqueues jobs.

The SchedulerWorker runs as a background asyncio task within FastAPI's lifespan
context (or the `python -m snackbase worker` process).

On startup it recalculates ``next_run_at`` for all enabled schedule hooks —
this handles missed executions when the server was down without retroactively
running them (the new ``next_run_at`` is always in the future).

Each poll tick:
1. Fetches hooks where ``trigger.type == "schedule"``, ``enabled = True``,
   and ``next_run_at <= now``.
2. For each due hook, enqueues a job with ``handler="scheduled_hook"`` and
   updates ``last_run_at`` / ``next_run_at`` atomically in the same transaction.

Usage (managed by app.py lifespan):
    worker = SchedulerWorker(db_manager.session, settings)
    await worker.start()
    ...
    await worker.stop()
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from snackbase.core.cron.parser import get_next_run
from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class SchedulerWorker:
    """Background worker that fires cron-scheduled hooks via the job queue.

    Args:
        session_factory: Async session factory (e.g., db_manager.session).
        settings: Application settings instance.
    """

    def __init__(self, session_factory: Any, settings: Any) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the scheduler background task."""
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="snackbase-scheduler")
        logger.info(
            "Scheduler worker started",
            poll_interval=self._settings.scheduler_poll_interval,
        )

    async def stop(self) -> None:
        """Stop the scheduler and wait for the current tick to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler worker stopped")

    async def _loop(self) -> None:
        """Main scheduler loop."""
        # On startup, recalculate all next_run_at values so missed executions
        # are skipped (not retroactively run).
        try:
            await self._recalculate_all_next_runs()
        except Exception as exc:
            logger.error("Scheduler startup recalculation failed", error=str(exc))

        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Scheduler tick error", error=str(exc))
            await asyncio.sleep(self._settings.scheduler_poll_interval)

    async def _recalculate_all_next_runs(self) -> None:
        """Recalculate next_run_at for all enabled schedule hooks.

        Called once on startup. Ensures next_run_at is always in the future
        so that missed executions are not retroactively fired.
        """
        from snackbase.infrastructure.persistence.repositories.hook_repository import (
            HookRepository,
        )

        now = datetime.now(UTC).replace(tzinfo=None)  # naive UTC

        async with self._session_factory() as session:
            repo = HookRepository(session)
            hooks = await repo.get_all_enabled_scheduled_hooks()

            recalculated = 0
            for hook in hooks:
                cron = hook.trigger.get("cron", "")
                try:
                    next_run = get_next_run(cron, now)
                    await repo.update_schedule_timestamps(hook.id, None, next_run)
                    recalculated += 1
                except ValueError as exc:
                    logger.warning(
                        "Skipping hook with invalid cron expression",
                        hook_id=hook.id,
                        cron=cron,
                        error=str(exc),
                    )

            await session.commit()

        if recalculated:
            logger.info("Scheduler recalculated next_run_at", count=recalculated)

    async def _tick(self) -> None:
        """Single scheduler tick: enqueue jobs for all due hooks."""
        from snackbase.infrastructure.persistence.models.job import JobModel
        from snackbase.infrastructure.persistence.repositories.hook_repository import (
            HookRepository,
        )
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        now = datetime.now(UTC).replace(tzinfo=None)  # naive UTC

        async with self._session_factory() as session:
            hook_repo = HookRepository(session)
            job_repo = JobRepository(session)

            due_hooks = await hook_repo.get_due_scheduled_hooks(now)
            if not due_hooks:
                return

            enqueued = 0
            for hook in due_hooks:
                cron = hook.trigger.get("cron", "")
                try:
                    next_run = get_next_run(cron, now)
                except ValueError as exc:
                    logger.warning(
                        "Invalid cron expression — disabling hook",
                        hook_id=hook.id,
                        cron=cron,
                        error=str(exc),
                    )
                    continue

                # Create job record in the same transaction so enqueue + timestamp
                # update are atomic (prevents double-firing on crash).
                job = JobModel(
                    handler="scheduled_hook",
                    payload={
                        "hook_id": hook.id,
                        "hook_name": hook.name,
                        "actions": hook.actions or [],
                    },
                    queue="scheduled",
                    account_id=hook.account_id,
                )
                await job_repo.create(job)

                await hook_repo.update_schedule_timestamps(
                    hook.id,
                    last_run_at=now,
                    next_run_at=next_run,
                )
                enqueued += 1

            await session.commit()

        if enqueued:
            logger.info("Scheduler enqueued jobs", count=enqueued)
