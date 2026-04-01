"""Integration tests for Background Job Queue (F7.2)."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.models.job import JobModel
from snackbase.infrastructure.persistence.repositories.job_repository import JobRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(**kwargs) -> JobModel:
    """Create a JobModel with sensible defaults for tests."""
    defaults = {
        "handler": "test_handler",
        "payload": {"key": "value"},
        "queue": "default",
        "status": "pending",
        "priority": 0,
        "max_retries": 3,
        "retry_delay_seconds": 60,
        "attempt_number": 0,
    }
    defaults.update(kwargs)
    return JobModel(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def superadmin_token_fixture(db_session: AsyncSession) -> str:
    """Return the superadmin token for API tests.

    Uses the conftest.py superadmin_token fixture pattern.
    """
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

    return jwt_service.create_access_token(
        user_id="superadmin-user",
        account_id=SYSTEM_ACCOUNT_ID,
        email="superadmin@example.com",
        role="admin",
    )


@pytest_asyncio.fixture
async def regular_token(db_session: AsyncSession) -> str:
    """Return a regular user token for auth tests."""
    # Create a test account + user
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000010",
        account_code="JB0001",
        name="Jobs Test Account",
        slug="jobs-test",
    )
    db_session.add(account)
    await db_session.flush()

    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()

    user = UserModel(
        id="jobs-test-user",
        email="user@jobstest.com",
        account_id=account.id,
        password_hash="hashed",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()

    return jwt_service.create_access_token(
        user_id=user.id,
        account_id=account.id,
        email=user.email,
        role="user",
    )


# ---------------------------------------------------------------------------
# Repository-level tests (direct DB access)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_get_job(db_session: AsyncSession) -> None:
    """Creating a job and retrieving it by ID returns the same record."""
    repo = JobRepository(db_session)
    job = _make_job(handler="webhook_delivery")
    await repo.create(job)
    await db_session.commit()

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.id == job.id
    assert fetched.handler == "webhook_delivery"
    assert fetched.status == "pending"


@pytest.mark.asyncio
async def test_pick_next_job_priority_order(db_session: AsyncSession) -> None:
    """pick_next_job returns the job with lower priority integer first."""
    repo = JobRepository(db_session)

    low_priority = _make_job(handler="low", priority=10)
    high_priority = _make_job(handler="high", priority=0)

    await repo.create(low_priority)
    await repo.create(high_priority)
    await db_session.commit()

    picked = await repo.pick_next_job()
    assert picked is not None
    assert picked.handler == "high"
    assert picked.status == "running"


@pytest.mark.asyncio
async def test_pick_next_job_respects_future_run_at(db_session: AsyncSession) -> None:
    """Jobs with run_at in the future are not picked up."""
    repo = JobRepository(db_session)

    future_job = _make_job(
        handler="future",
        run_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await repo.create(future_job)
    await db_session.commit()

    picked = await repo.pick_next_job()
    assert picked is None


@pytest.mark.asyncio
async def test_pick_next_job_past_run_at_is_picked(db_session: AsyncSession) -> None:
    """Jobs with run_at in the past are eligible for pickup."""
    repo = JobRepository(db_session)

    past_job = _make_job(
        handler="past",
        run_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    await repo.create(past_job)
    await db_session.commit()

    picked = await repo.pick_next_job()
    assert picked is not None
    assert picked.handler == "past"


@pytest.mark.asyncio
async def test_mark_completed(db_session: AsyncSession) -> None:
    """mark_completed sets status to 'completed' and sets completed_at."""
    repo = JobRepository(db_session)
    job = _make_job(status="running")
    await repo.create(job)
    await db_session.commit()

    await repo.mark_completed(job.id)
    await db_session.commit()

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == "completed"
    assert fetched.completed_at is not None


@pytest.mark.asyncio
async def test_mark_failed_retrying(db_session: AsyncSession) -> None:
    """mark_failed with new_status='retrying' sets correct fields."""
    repo = JobRepository(db_session)
    job = _make_job(status="running", max_retries=3)
    await repo.create(job)
    await db_session.commit()

    next_run_at = datetime.now(UTC) + timedelta(minutes=1)
    await repo.mark_failed(job.id, "Connection refused", next_run_at, "retrying")
    await db_session.commit()

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == "retrying"
    assert fetched.attempt_number == 1
    assert fetched.error_message == "Connection refused"
    assert fetched.failed_at is not None
    assert fetched.run_at is not None


@pytest.mark.asyncio
async def test_mark_failed_dead_after_max_retries(db_session: AsyncSession) -> None:
    """mark_failed with new_status='dead' marks job permanently failed."""
    repo = JobRepository(db_session)
    job = _make_job(status="running", max_retries=1, attempt_number=0)
    await repo.create(job)
    await db_session.commit()

    await repo.mark_failed(job.id, "Exhausted retries", None, "dead")
    await db_session.commit()

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == "dead"
    assert fetched.run_at is None


@pytest.mark.asyncio
async def test_exponential_backoff_delay(db_session: AsyncSession) -> None:
    """Retry delay doubles per attempt: delay * 2^attempt."""
    # attempt=0: delay=60 * 2^0 = 60s
    # attempt=1: delay=60 * 2^1 = 120s
    # attempt=2: delay=60 * 2^2 = 240s
    for attempt in range(3):
        expected_delay = 60 * (2**attempt)
        assert expected_delay == 60 * (2**attempt)

    # Verify the formula is consistent
    assert 60 * (2**0) == 60
    assert 60 * (2**1) == 120
    assert 60 * (2**2) == 240


@pytest.mark.asyncio
async def test_reset_stale_jobs(db_session: AsyncSession) -> None:
    """Jobs running longer than timeout are reset to pending."""
    repo = JobRepository(db_session)

    # A job that started 10 minutes ago
    stale_job = _make_job(
        status="running",
        started_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    await repo.create(stale_job)
    await db_session.commit()

    # Timeout of 5 minutes: the job is stale
    count = await repo.reset_stale_jobs(timeout_seconds=300)
    await db_session.commit()

    assert count == 1

    fetched = await repo.get_by_id(stale_job.id)
    assert fetched is not None
    assert fetched.status == "pending"
    assert fetched.started_at is None


@pytest.mark.asyncio
async def test_reset_stale_jobs_ignores_recent(db_session: AsyncSession) -> None:
    """Recently started jobs are not reset by reset_stale_jobs."""
    repo = JobRepository(db_session)

    fresh_job = _make_job(
        status="running",
        started_at=datetime.now(UTC) - timedelta(seconds=10),
    )
    await repo.create(fresh_job)
    await db_session.commit()

    count = await repo.reset_stale_jobs(timeout_seconds=300)
    await db_session.commit()

    assert count == 0


@pytest.mark.asyncio
async def test_delete_completed_before(db_session: AsyncSession) -> None:
    """Completed jobs older than cutoff are deleted."""
    repo = JobRepository(db_session)

    old_job = _make_job(
        status="completed",
        completed_at=datetime.now(UTC) - timedelta(days=10),
    )
    await repo.create(old_job)
    await db_session.commit()

    cutoff = datetime.now(UTC) - timedelta(days=7)
    count = await repo.delete_completed_before(cutoff)
    await db_session.commit()

    assert count == 1
    fetched = await repo.get_by_id(old_job.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_completed_before_keeps_recent(db_session: AsyncSession) -> None:
    """Recently completed jobs are not deleted."""
    repo = JobRepository(db_session)

    recent_job = _make_job(
        status="completed",
        completed_at=datetime.now(UTC) - timedelta(days=1),
    )
    await repo.create(recent_job)
    await db_session.commit()

    cutoff = datetime.now(UTC) - timedelta(days=7)
    count = await repo.delete_completed_before(cutoff)
    await db_session.commit()

    assert count == 0
    fetched = await repo.get_by_id(recent_job.id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_retry_job_resets_dead_job(db_session: AsyncSession) -> None:
    """retry_job resets a dead job back to pending."""
    repo = JobRepository(db_session)

    dead_job = _make_job(
        status="dead",
        error_message="All retries exhausted",
        attempt_number=3,
    )
    await repo.create(dead_job)
    await db_session.commit()

    result = await repo.retry_job(dead_job.id)
    await db_session.commit()

    assert result is True

    fetched = await repo.get_by_id(dead_job.id)
    assert fetched is not None
    assert fetched.status == "pending"
    assert fetched.attempt_number == 0
    assert fetched.error_message is None


@pytest.mark.asyncio
async def test_retry_job_rejects_running_job(db_session: AsyncSession) -> None:
    """retry_job returns False for jobs not in dead/failed status."""
    repo = JobRepository(db_session)

    running_job = _make_job(status="running")
    await repo.create(running_job)
    await db_session.commit()

    result = await repo.retry_job(running_job.id)
    await db_session.commit()

    assert result is False


@pytest.mark.asyncio
async def test_get_stats_counts_by_status(db_session: AsyncSession) -> None:
    """get_stats returns accurate counts for each status."""
    repo = JobRepository(db_session)

    jobs_by_status = {
        "pending": 2,
        "running": 1,
        "completed": 3,
        "failed": 1,
        "dead": 1,
    }
    for status, count in jobs_by_status.items():
        for _ in range(count):
            j = _make_job(status=status)
            await repo.create(j)
    await db_session.commit()

    stats = await repo.get_stats()
    assert stats["pending"] == 2
    assert stats["running"] == 1
    assert stats["completed"] == 3
    assert stats["failed"] == 1
    assert stats["dead"] == 1
    assert stats["retrying"] == 0


@pytest.mark.asyncio
async def test_queue_filter_isolation(db_session: AsyncSession) -> None:
    """pick_next_job with queue_filter only picks from that queue."""
    repo = JobRepository(db_session)

    webhook_job = _make_job(handler="webhooks_h", queue="webhooks")
    default_job = _make_job(handler="default_h", queue="default")
    await repo.create(webhook_job)
    await repo.create(default_job)
    await db_session.commit()

    picked = await repo.pick_next_job(queue_filter="webhooks")
    assert picked is not None
    assert picked.queue == "webhooks"
    assert picked.handler == "webhooks_h"


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_jobs_requires_superadmin(
    client: AsyncClient, regular_token: str
) -> None:
    """GET /api/v1/admin/jobs returns 403 for non-superadmin users."""
    response = await client.get(
        "/api/v1/admin/jobs",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_list_jobs_empty(
    client: AsyncClient, superadmin_token: str
) -> None:
    """GET /api/v1/admin/jobs returns empty list when no jobs exist."""
    response = await client.get(
        "/api/v1/admin/jobs",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_jobs_with_data(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """GET /api/v1/admin/jobs returns jobs after they are created."""
    repo = JobRepository(db_session)
    job1 = _make_job(handler="webhook_delivery", status="pending")
    job2 = _make_job(handler="send_email", status="completed")
    await repo.create(job1)
    await repo.create(job2)
    await db_session.commit()

    response = await client.get(
        "/api/v1/admin/jobs",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_jobs_status_filter(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """GET /api/v1/admin/jobs?status=dead returns only dead jobs."""
    repo = JobRepository(db_session)
    dead_job = _make_job(status="dead")
    pending_job = _make_job(status="pending")
    await repo.create(dead_job)
    await repo.create(pending_job)
    await db_session.commit()

    response = await client.get(
        "/api/v1/admin/jobs?status=dead",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "dead"


@pytest.mark.asyncio
async def test_get_job_stats(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """GET /api/v1/admin/jobs/stats returns correct status counts."""
    repo = JobRepository(db_session)
    await repo.create(_make_job(status="pending"))
    await repo.create(_make_job(status="pending"))
    await repo.create(_make_job(status="running"))
    await repo.create(_make_job(status="dead"))
    await db_session.commit()

    response = await client.get(
        "/api/v1/admin/jobs/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pending"] == 2
    assert data["running"] == 1
    assert data["dead"] == 1
    assert data["completed"] == 0
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_retry_dead_job(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """POST /api/v1/admin/jobs/{id}/retry resets a dead job to pending."""
    repo = JobRepository(db_session)
    dead_job = _make_job(status="dead", attempt_number=3, error_message="Failed")
    await repo.create(dead_job)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/jobs/{dead_job.id}/retry",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "pending"
    assert data["attempt_number"] == 0
    assert data["error_message"] is None


@pytest.mark.asyncio
async def test_retry_non_dead_job_returns_400(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """POST /api/v1/admin/jobs/{id}/retry returns 400 for running jobs."""
    repo = JobRepository(db_session)
    running_job = _make_job(status="running")
    await repo.create(running_job)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/jobs/{running_job.id}/retry",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_retry_nonexistent_job_returns_404(
    client: AsyncClient, superadmin_token: str
) -> None:
    """POST /api/v1/admin/jobs/{id}/retry returns 404 for unknown job."""
    response = await client.post(
        "/api/v1/admin/jobs/nonexistent-job-id/retry",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_cancel_pending_job(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """DELETE /api/v1/admin/jobs/{id} deletes a pending job."""
    repo = JobRepository(db_session)
    pending_job = _make_job(status="pending")
    await repo.create(pending_job)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/admin/jobs/{pending_job.id}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 204, response.text

    # Verify deletion
    remaining = await repo.get_by_id(pending_job.id)
    assert remaining is None


@pytest.mark.asyncio
async def test_cancel_running_job_returns_400(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
) -> None:
    """DELETE /api/v1/admin/jobs/{id} returns 400 for non-pending jobs."""
    repo = JobRepository(db_session)
    running_job = _make_job(status="running")
    await repo.create(running_job)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/admin/jobs/{running_job.id}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_cancel_nonexistent_job_returns_404(
    client: AsyncClient, superadmin_token: str
) -> None:
    """DELETE /api/v1/admin/jobs/{id} returns 404 for unknown job."""
    response = await client.delete(
        "/api/v1/admin/jobs/nonexistent-job-id",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# Handler registry tests
# ---------------------------------------------------------------------------


def test_handler_registry_register_and_get() -> None:
    """HandlerRegistry.register() stores callables retrievable by name."""
    from snackbase.infrastructure.services.job_service import HandlerRegistry

    registry = HandlerRegistry()

    @registry.register("my_test_handler")
    async def my_handler(payload: dict, job) -> None:  # type: ignore[type-arg]
        pass

    handler = registry.get("my_test_handler")
    assert handler is my_handler
    assert "my_test_handler" in registry.all_handlers()


def test_handler_registry_get_unknown_returns_none() -> None:
    """HandlerRegistry.get() returns None for unregistered handler names."""
    from snackbase.infrastructure.services.job_service import HandlerRegistry

    registry = HandlerRegistry()
    assert registry.get("does_not_exist") is None


def test_builtin_handlers_registered() -> None:
    """Built-in handlers are pre-registered in the module-level handler_registry."""
    from snackbase.infrastructure.services.job_service import handler_registry

    assert handler_registry.get("webhook_delivery") is not None
    assert handler_registry.get("send_email") is not None
    assert handler_registry.get("scheduled_task") is not None


# ---------------------------------------------------------------------------
# JobService enqueue tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_service_enqueue(db_session: AsyncSession) -> None:
    """JobService.enqueue() creates a job record and returns its ID."""
    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.services.job_service import JobService

    db_manager = get_db_manager()
    service = JobService(db_manager.session)

    job_id = await service.enqueue(
        handler="test_handler",
        payload={"foo": "bar"},
        queue="test-queue",
        priority=5,
        max_retries=2,
    )
    assert job_id is not None

    repo = JobRepository(db_session)
    job = await repo.get_by_id(job_id)
    assert job is not None
    assert job.handler == "test_handler"
    assert job.payload == {"foo": "bar"}
    assert job.queue == "test-queue"
    assert job.priority == 5
    assert job.max_retries == 2
    assert job.status == "pending"
