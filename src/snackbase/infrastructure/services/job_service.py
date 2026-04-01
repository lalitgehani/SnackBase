"""Background job queue: handler registry, job service, and worker.

This module provides:
- HandlerRegistry: maps handler name strings to async Python callables
- JobService: enqueue helper that creates job records in the database
- JobWorker: asyncio background task that polls for and executes jobs

Usage:
    # Enqueue a job
    service = JobService(db_manager.session)
    job_id = await service.enqueue("webhook_delivery", payload={...})

    # Register a custom handler
    @handler_registry.register("my_handler")
    async def my_handler(payload: dict, job: JobModel) -> None:
        ...

    # Start/stop the worker (done by app.py lifespan)
    worker = JobWorker(db_manager.session, settings)
    await worker.start()
    ...
    await worker.stop()
"""

import asyncio
import base64
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from snackbase.core.logging import get_logger

if TYPE_CHECKING:
    from snackbase.infrastructure.persistence.models.job import JobModel

# Type alias for handler callables
JobHandler = Callable[[dict, Any], Awaitable[None]]

logger = get_logger(__name__)


class HandlerRegistry:
    """Registry mapping handler name strings to async callable functions.

    Provides a decorator-based registration API:

        @handler_registry.register("my_handler")
        async def my_handler(payload: dict, job: JobModel) -> None:
            ...
    """

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, name: str) -> Callable[[JobHandler], JobHandler]:
        """Register a handler function under the given name.

        Args:
            name: The handler identifier used in job records.

        Returns:
            Decorator that registers and returns the function unchanged.
        """

        def decorator(fn: JobHandler) -> JobHandler:
            self._handlers[name] = fn
            return fn

        return decorator

    def get(self, name: str) -> JobHandler | None:
        """Look up a handler by name.

        Returns:
            The handler callable, or None if not registered.
        """
        return self._handlers.get(name)

    def all_handlers(self) -> list[str]:
        """Return list of all registered handler names."""
        return list(self._handlers.keys())


# Module-level singleton — import and use this directly
handler_registry = HandlerRegistry()


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------


@handler_registry.register("webhook_delivery")
async def _handle_webhook_delivery(payload: dict, job: "JobModel") -> None:
    """Execute a single webhook delivery attempt.

    Payload keys:
        delivery_id: str — ID of the WebhookDeliveryModel record
        url: str — destination URL
        secret: str — HMAC signing secret
        custom_headers: dict — extra HTTP headers
        payload_b64: str — base64-encoded request body bytes
        timeout_seconds: int — per-request HTTP timeout
    """
    from snackbase.infrastructure.webhooks.webhook_service import attempt_webhook_delivery

    delivery_id: str = payload["delivery_id"]
    url: str = payload["url"]
    secret: str = payload["secret"]
    custom_headers: dict = payload.get("custom_headers") or {}
    payload_bytes: bytes = base64.b64decode(payload["payload_b64"])
    timeout_seconds: int = payload.get("timeout_seconds", 30)

    await attempt_webhook_delivery(
        delivery_id=delivery_id,
        url=url,
        secret=secret,
        custom_headers=custom_headers,
        payload_bytes=payload_bytes,
        timeout_seconds=timeout_seconds,
    )


@handler_registry.register("send_email")
async def _handle_send_email(payload: dict, job: "JobModel") -> None:
    """Send an email via the configured email provider.

    Payload keys:
        account_id: str — account context for provider lookup
        to_email: str — recipient email address
        subject: str — email subject
        template_name: str | None — template to render
        template_vars: dict | None — variables for template rendering
        html_content: str | None — raw HTML (if no template)
        text_content: str | None — raw text (if no template)
    """
    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.services.email_service import EmailService

    db_manager = get_db_manager()
    async with db_manager.session() as session:
        email_service = EmailService(session)
        await email_service.send_email(
            account_id=payload["account_id"],
            to_email=payload["to_email"],
            subject=payload["subject"],
            template_name=payload.get("template_name"),
            template_vars=payload.get("template_vars") or {},
            html_content=payload.get("html_content"),
            text_content=payload.get("text_content"),
        )


@handler_registry.register("scheduled_task")
async def _handle_scheduled_task(payload: dict, job: "JobModel") -> None:
    """Placeholder handler for F7.3 scheduled tasks.

    Payload keys:
        task_type: str — type identifier for the scheduled task
        args: dict — task-specific arguments
    """
    task_type = payload.get("task_type", "unknown")
    logger.info("Scheduled task executed", task_type=task_type, job_id=job.id)


# ---------------------------------------------------------------------------
# JobService — enqueue helper
# ---------------------------------------------------------------------------


class JobService:
    """Helper for enqueuing background jobs.

    Args:
        session_factory: Async session factory (e.g., db_manager.session).
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def enqueue(
        self,
        handler: str,
        payload: dict,
        *,
        queue: str = "default",
        priority: int = 0,
        run_at: datetime | None = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
        account_id: str | None = None,
        created_by: str | None = None,
    ) -> str:
        """Create a job record in the database.

        Args:
            handler: Registered handler name (must exist in handler_registry).
            payload: JSON-serializable dict passed to the handler.
            queue: Queue name (default: "default").
            priority: Lower integer = higher priority (default: 0).
            run_at: Earliest execution time (None = execute immediately).
            max_retries: Maximum retry attempts before marking dead.
            retry_delay_seconds: Base retry delay; exponential backoff applied.
            account_id: Account context (None for system-level jobs).
            created_by: User ID of enqueueing user (None for system jobs).

        Returns:
            The newly created job ID.
        """
        from snackbase.infrastructure.persistence.models.job import JobModel
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        job = JobModel(
            queue=queue,
            handler=handler,
            payload=payload,
            status="pending",
            priority=priority,
            run_at=run_at,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            account_id=account_id,
            created_by=created_by,
        )
        async with self._session_factory() as session:
            repo = JobRepository(session)
            await repo.create(job)
            await session.commit()
        return job.id


# ---------------------------------------------------------------------------
# JobWorker — asyncio background task
# ---------------------------------------------------------------------------


class JobWorker:
    """Asyncio background worker that polls and executes queued jobs.

    Runs as a long-lived asyncio Task within FastAPI's lifespan context,
    or as a standalone process via `python -m snackbase worker`.

    Features:
    - Priority + FIFO ordering via JobRepository.pick_next_job()
    - Configurable poll interval (default 1s)
    - asyncio.wait_for() enforces per-job execution timeout
    - Exponential backoff retries: delay * 2^attempt_number
    - Stale job recovery (every 60 polls)
    - Retention cleanup of completed jobs (every 86400 polls)
    - Optional queue_filter for dedicated queue workers

    Args:
        session_factory: Async session factory (e.g., db_manager.session).
        settings: Application settings instance.
        queue_filter: If set, only pick jobs from this queue.
    """

    def __init__(
        self,
        session_factory: Any,
        settings: Any,
        queue_filter: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._queue_filter = queue_filter
        self._running = False
        self._task: asyncio.Task | None = None
        self._poll_count = 0

    async def start(self) -> None:
        """Start the worker background task."""
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="snackbase-job-worker")
        logger.info(
            "Job worker started",
            poll_interval=self._settings.job_worker_poll_interval,
            queue_filter=self._queue_filter,
        )

    async def stop(self) -> None:
        """Stop the worker and wait for the current tick to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Job worker stopped")

    async def _loop(self) -> None:
        """Main worker loop: polls at configured interval, catches all errors."""
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Job worker tick error", error=str(exc))
            await asyncio.sleep(self._settings.job_worker_poll_interval)

    async def _tick(self) -> None:
        """Single worker tick: maintenance + pick-and-execute one job."""
        self._poll_count += 1

        # Reset stale jobs every 60 polls
        if self._poll_count % 60 == 0:
            await self._reset_stale()

        # Retention cleanup every 86400 polls (~24h at 1s interval)
        if self._poll_count % 86400 == 0:
            await self._cleanup_old_jobs()

        # Pick and execute one job
        await self._process_one_job()

    async def _reset_stale(self) -> None:
        """Reset running jobs that have exceeded the execution timeout."""
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        async with self._session_factory() as session:
            repo = JobRepository(session)
            count = await repo.reset_stale_jobs(self._settings.job_execution_timeout)
            await session.commit()
        if count:
            logger.info("Reset stale jobs", count=count)

    async def _cleanup_old_jobs(self) -> None:
        """Delete completed jobs older than the retention period."""
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        cutoff = datetime.now(UTC) - timedelta(days=self._settings.job_retention_days)
        async with self._session_factory() as session:
            repo = JobRepository(session)
            count = await repo.delete_completed_before(cutoff)
            await session.commit()
        if count:
            logger.info("Deleted old completed jobs", count=count, cutoff=str(cutoff))

    async def _process_one_job(self) -> None:
        """Pick the next available job and execute it."""
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        # Pick and claim next job
        async with self._session_factory() as session:
            repo = JobRepository(session)
            job = await repo.pick_next_job(queue_filter=self._queue_filter)
            if job is None:
                return

            # Capture job fields before session closes
            job_id = job.id
            handler_name = job.handler
            payload = dict(job.payload)
            attempt = job.attempt_number
            max_retries = job.max_retries
            retry_delay = job.retry_delay_seconds

            await session.commit()

        # Look up the handler
        handler = handler_registry.get(handler_name)
        if handler is None:
            logger.warning("Unknown job handler", handler=handler_name, job_id=job_id)
            await self._fail_job(
                job_id=job_id,
                error=f"Unknown handler: {handler_name}",
                attempt=attempt,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
            return

        # Build a lightweight snapshot to pass to the handler.
        # The session is already closed so we cannot pass the ORM object;
        # SimpleNamespace gives attribute access without SQLAlchemy overhead.
        import types

        job_snapshot = types.SimpleNamespace(
            id=job_id,
            handler=handler_name,
            payload=payload,
            attempt_number=attempt,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay,
        )

        # Execute with timeout
        try:
            await asyncio.wait_for(
                handler(payload, job_snapshot),
                timeout=float(self._settings.job_execution_timeout),
            )
        except (asyncio.TimeoutError, TimeoutError):
            error = f"Job timed out after {self._settings.job_execution_timeout}s"
            logger.warning("Job timed out", job_id=job_id, handler=handler_name)
            await self._fail_job(job_id, error, attempt, max_retries, retry_delay)
            return
        except asyncio.CancelledError:
            # Worker is shutting down; reset job to pending so it is retried later
            async with self._session_factory() as session:
                repo = JobRepository(session)
                await repo.mark_failed(job_id, "Worker cancelled", None, "pending")
                await session.commit()
            raise
        except Exception as exc:
            logger.warning(
                "Job execution failed",
                job_id=job_id,
                handler=handler_name,
                error=str(exc),
            )
            await self._fail_job(job_id, str(exc), attempt, max_retries, retry_delay)
            return

        # Success
        async with self._session_factory() as session:
            repo = JobRepository(session)
            await repo.mark_completed(job_id)
            await session.commit()
        logger.info("Job completed", job_id=job_id, handler=handler_name)

    async def _fail_job(
        self,
        job_id: str,
        error: str,
        attempt: int,
        max_retries: int,
        retry_delay: int,
    ) -> None:
        """Compute retry schedule and persist failure."""
        from snackbase.infrastructure.persistence.repositories.job_repository import (
            JobRepository,
        )

        new_attempt = attempt + 1
        if new_attempt >= max_retries:
            new_status = "dead"
            next_run_at = None
        else:
            new_status = "retrying"
            # Exponential backoff: retry_delay * 2^attempt
            delay_seconds = retry_delay * (2**attempt)
            next_run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)

        async with self._session_factory() as session:
            repo = JobRepository(session)
            await repo.mark_failed(job_id, error, next_run_at, new_status)
            await session.commit()

        logger.info(
            "Job failed",
            job_id=job_id,
            new_status=new_status,
            attempt=new_attempt,
            next_run_at=str(next_run_at) if next_run_at else None,
        )
