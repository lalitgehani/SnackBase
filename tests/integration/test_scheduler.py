"""Integration tests for Cron Scheduling Infrastructure (F7.3).

Covers:
- HookRepository CRUD and scheduler queries
- Scheduler fires due hooks and enqueues jobs
- Timestamp updates after execution
- Disabled hooks are skipped
- Startup next_run_at recalculation (missed execution recovery)
- Per-account schedule hook count
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.infrastructure.persistence.models.hook import HookModel
from snackbase.infrastructure.persistence.models.job import JobModel
from snackbase.infrastructure.persistence.repositories.hook_repository import HookRepository
from snackbase.infrastructure.persistence.repositories.job_repository import JobRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schedule_hook(account_id: str, cron: str = "*/5 * * * *", **kwargs) -> HookModel:
    """Create a schedule-type HookModel with sensible defaults."""
    defaults = {
        "account_id": account_id,
        "name": "Test Schedule",
        "trigger": {"type": "schedule", "cron": cron},
        "actions": [],
        "enabled": True,
    }
    defaults.update(kwargs)
    return HookModel(**defaults)


def _make_event_hook(account_id: str, **kwargs) -> HookModel:
    """Create an event-type HookModel."""
    defaults = {
        "account_id": account_id,
        "name": "Test Event Hook",
        "trigger": {"type": "event", "event": "records.create"},
        "actions": [],
        "enabled": True,
    }
    defaults.update(kwargs)
    return HookModel(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession) -> AccountModel:
    """Create a test account for hook tests."""
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000099",
        account_code="HK0001",
        name="Hook Test Account",
        slug="hook-test",
    )
    db_session.add(account)
    await db_session.commit()
    return account


# ---------------------------------------------------------------------------
# HookRepository — CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_get_hook(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)
    hook = _make_schedule_hook(test_account.id)
    created = await repo.create(hook)
    await db_session.commit()

    retrieved = await repo.get(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.trigger["type"] == "schedule"
    assert retrieved.trigger["cron"] == "*/5 * * * *"
    assert retrieved.enabled is True


@pytest.mark.asyncio
async def test_get_nonexistent_hook(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)
    result = await repo.get("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_delete_hook(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)
    hook = _make_schedule_hook(test_account.id)
    await repo.create(hook)
    await db_session.commit()

    await repo.delete(hook.id)
    await db_session.commit()

    assert await repo.get(hook.id) is None


@pytest.mark.asyncio
async def test_list_for_account(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)

    for i in range(3):
        h = _make_schedule_hook(test_account.id, name=f"Hook {i}")
        await repo.create(h)
    await db_session.commit()

    hooks, total = await repo.list_for_account(test_account.id)
    assert total == 3
    assert len(hooks) == 3


@pytest.mark.asyncio
async def test_list_filter_by_trigger_type(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)

    await repo.create(_make_schedule_hook(test_account.id, name="Schedule"))
    await repo.create(_make_event_hook(test_account.id))
    await db_session.commit()

    sched_hooks, sched_count = await repo.list_for_account(
        test_account.id, trigger_type="schedule"
    )
    event_hooks, event_count = await repo.list_for_account(
        test_account.id, trigger_type="event"
    )

    assert sched_count == 1
    assert event_count == 1
    assert sched_hooks[0].trigger["type"] == "schedule"
    assert event_hooks[0].trigger["type"] == "event"


@pytest.mark.asyncio
async def test_list_pagination(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)

    for i in range(5):
        await repo.create(_make_schedule_hook(test_account.id, name=f"Hook {i}"))
    await db_session.commit()

    page1, total = await repo.list_for_account(test_account.id, offset=0, limit=3)
    page2, _ = await repo.list_for_account(test_account.id, offset=3, limit=3)

    assert total == 5
    assert len(page1) == 3
    assert len(page2) == 2


# ---------------------------------------------------------------------------
# Scheduler queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_due_scheduled_hooks_returns_overdue(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    hook = _make_schedule_hook(test_account.id, next_run_at=past)
    await repo.create(hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due = await repo.get_due_scheduled_hooks(now)
    assert len(due) == 1
    assert due[0].id == hook.id


@pytest.mark.asyncio
async def test_get_due_scheduled_hooks_skips_future(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)
    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
    hook = _make_schedule_hook(test_account.id, next_run_at=future)
    await repo.create(hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due = await repo.get_due_scheduled_hooks(now)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_get_due_scheduled_hooks_skips_disabled(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    hook = _make_schedule_hook(test_account.id, next_run_at=past, enabled=False)
    await repo.create(hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due = await repo.get_due_scheduled_hooks(now)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_get_due_scheduled_hooks_skips_null_next_run(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)
    hook = _make_schedule_hook(test_account.id, next_run_at=None)
    await repo.create(hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due = await repo.get_due_scheduled_hooks(now)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_get_due_scheduled_hooks_skips_event_type(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    # Event-type hook with past next_run_at should NOT appear
    event_hook = _make_event_hook(test_account.id)
    event_hook.next_run_at = past
    await repo.create(event_hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due = await repo.get_due_scheduled_hooks(now)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_update_schedule_timestamps(db_session: AsyncSession, test_account: AccountModel):
    repo = HookRepository(db_session)
    hook = _make_schedule_hook(test_account.id)
    await repo.create(hook)
    await db_session.commit()

    last_run = datetime(2026, 1, 1, 9, 0, 0)
    next_run = datetime(2026, 1, 1, 9, 5, 0)
    await repo.update_schedule_timestamps(hook.id, last_run, next_run)
    await db_session.commit()

    await db_session.refresh(hook)
    assert hook.last_run_at is not None
    assert hook.next_run_at is not None


@pytest.mark.asyncio
async def test_count_scheduled_hooks_for_account(
    db_session: AsyncSession, test_account: AccountModel
):
    repo = HookRepository(db_session)

    # Add 2 schedule and 1 event hook
    await repo.create(_make_schedule_hook(test_account.id, name="S1"))
    await repo.create(_make_schedule_hook(test_account.id, name="S2"))
    await repo.create(_make_event_hook(test_account.id))
    await db_session.commit()

    count = await repo.count_scheduled_hooks_for_account(test_account.id)
    assert count == 2


# ---------------------------------------------------------------------------
# SchedulerWorker — tick and startup recalculation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_tick_enqueues_job_for_due_hook(
    db_session: AsyncSession, test_account: AccountModel
):
    """Scheduler tick should enqueue a job when a hook is due."""
    hook_repo = HookRepository(db_session)
    job_repo = JobRepository(db_session)

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
    hook = _make_schedule_hook(test_account.id, cron="*/5 * * * *", next_run_at=past)
    await hook_repo.create(hook)
    await db_session.commit()

    # Simulate what SchedulerWorker._tick does (without asyncio task overhead)
    from snackbase.core.cron.parser import get_next_run

    now = datetime.now(UTC).replace(tzinfo=None)
    due_hooks = await hook_repo.get_due_scheduled_hooks(now)
    assert len(due_hooks) == 1

    for h in due_hooks:
        cron = h.trigger["cron"]
        next_run = get_next_run(cron, now)
        job = JobModel(
            handler="scheduled_hook",
            payload={"hook_id": h.id, "hook_name": h.name, "actions": h.actions or []},
            queue="scheduled",
            account_id=h.account_id,
        )
        await job_repo.create(job)
        await hook_repo.update_schedule_timestamps(h.id, now, next_run)

    await db_session.commit()

    # Verify job was created
    result = await db_session.execute(
        select(JobModel).where(JobModel.account_id == test_account.id)
    )
    jobs = list(result.scalars().all())
    assert len(jobs) == 1
    assert jobs[0].handler == "scheduled_hook"
    assert jobs[0].payload["hook_id"] == hook.id


@pytest.mark.asyncio
async def test_scheduler_tick_updates_timestamps(
    db_session: AsyncSession, test_account: AccountModel
):
    """After a tick, last_run_at and next_run_at should be updated."""
    hook_repo = HookRepository(db_session)
    job_repo = JobRepository(db_session)

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
    hook = _make_schedule_hook(test_account.id, cron="*/5 * * * *", next_run_at=past)
    await hook_repo.create(hook)
    await db_session.commit()

    from snackbase.core.cron.parser import get_next_run

    now = datetime.now(UTC).replace(tzinfo=None)
    due_hooks = await hook_repo.get_due_scheduled_hooks(now)

    for h in due_hooks:
        next_run = get_next_run(h.trigger["cron"], now)
        job = JobModel(
            handler="scheduled_hook",
            payload={"hook_id": h.id, "actions": []},
            queue="scheduled",
            account_id=h.account_id,
        )
        await job_repo.create(job)
        await hook_repo.update_schedule_timestamps(h.id, now, next_run)

    await db_session.commit()

    # Reload and verify timestamps
    updated = await hook_repo.get(hook.id)
    assert updated is not None
    assert updated.last_run_at is not None
    # next_run_at should be in the future
    assert updated.next_run_at is not None
    assert updated.next_run_at > now


@pytest.mark.asyncio
async def test_scheduler_tick_skips_disabled_hook(
    db_session: AsyncSession, test_account: AccountModel
):
    """Disabled hooks should not be picked up by the scheduler."""
    hook_repo = HookRepository(db_session)

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
    hook = _make_schedule_hook(
        test_account.id, cron="*/5 * * * *", next_run_at=past, enabled=False
    )
    await hook_repo.create(hook)
    await db_session.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    due_hooks = await hook_repo.get_due_scheduled_hooks(now)
    assert len(due_hooks) == 0


@pytest.mark.asyncio
async def test_recalculate_all_next_runs_sets_future_times(
    db_session: AsyncSession, test_account: AccountModel
):
    """On startup, all schedule hooks should get next_run_at in the future."""
    hook_repo = HookRepository(db_session)

    # Hook with past or NULL next_run_at
    hook1 = _make_schedule_hook(test_account.id, cron="*/5 * * * *", next_run_at=None)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    hook2 = _make_schedule_hook(test_account.id, cron="0 9 * * *", next_run_at=past)
    await hook_repo.create(hook1)
    await hook_repo.create(hook2)
    await db_session.commit()

    # Simulate _recalculate_all_next_runs
    from snackbase.core.cron.parser import get_next_run

    now = datetime.now(UTC).replace(tzinfo=None)
    hooks = await hook_repo.get_all_enabled_scheduled_hooks()
    for h in hooks:
        cron = h.trigger.get("cron", "")
        next_run = get_next_run(cron, now)
        await hook_repo.update_schedule_timestamps(h.id, None, next_run)
    await db_session.commit()

    # Verify both hooks now have future next_run_at
    updated1 = await hook_repo.get(hook1.id)
    updated2 = await hook_repo.get(hook2.id)
    assert updated1.next_run_at is not None
    assert updated1.next_run_at > now
    assert updated2.next_run_at is not None
    assert updated2.next_run_at > now


@pytest.mark.asyncio
async def test_recalculate_skips_event_hooks(
    db_session: AsyncSession, test_account: AccountModel
):
    """get_all_enabled_scheduled_hooks should only return schedule-type hooks."""
    hook_repo = HookRepository(db_session)

    await hook_repo.create(_make_schedule_hook(test_account.id, name="Schedule"))
    await hook_repo.create(_make_event_hook(test_account.id))
    await db_session.commit()

    hooks = await hook_repo.get_all_enabled_scheduled_hooks()
    assert len(hooks) == 1
    assert hooks[0].trigger["type"] == "schedule"


@pytest.mark.asyncio
async def test_no_double_fire_after_timestamp_update(
    db_session: AsyncSession, test_account: AccountModel
):
    """After firing, hook should not appear in the next due query."""
    hook_repo = HookRepository(db_session)
    job_repo = JobRepository(db_session)

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
    hook = _make_schedule_hook(test_account.id, cron="*/5 * * * *", next_run_at=past)
    await hook_repo.create(hook)
    await db_session.commit()

    from snackbase.core.cron.parser import get_next_run

    now = datetime.now(UTC).replace(tzinfo=None)
    due_hooks = await hook_repo.get_due_scheduled_hooks(now)
    assert len(due_hooks) == 1

    # Simulate tick: update timestamps
    next_run = get_next_run(due_hooks[0].trigger["cron"], now)
    job = JobModel(
        handler="scheduled_hook",
        payload={"hook_id": hook.id, "actions": []},
        queue="scheduled",
        account_id=hook.account_id,
    )
    await job_repo.create(job)
    await hook_repo.update_schedule_timestamps(hook.id, now, next_run)
    await db_session.commit()

    # Second tick: hook should not be due anymore
    due_again = await hook_repo.get_due_scheduled_hooks(now)
    assert len(due_again) == 0


@pytest.mark.asyncio
async def test_scheduled_hook_job_payload_contains_hook_id(
    db_session: AsyncSession, test_account: AccountModel
):
    """Job payload should include hook_id for handler context."""
    hook_repo = HookRepository(db_session)
    job_repo = JobRepository(db_session)

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    hook = _make_schedule_hook(
        test_account.id,
        cron="* * * * *",
        next_run_at=past,
        name="My Schedule",
        actions=[{"type": "send_webhook", "url": "https://example.com"}],
    )
    await hook_repo.create(hook)
    await db_session.commit()

    from snackbase.core.cron.parser import get_next_run

    now = datetime.now(UTC).replace(tzinfo=None)
    due_hooks = await hook_repo.get_due_scheduled_hooks(now)

    for h in due_hooks:
        next_run = get_next_run(h.trigger["cron"], now)
        job = JobModel(
            handler="scheduled_hook",
            payload={
                "hook_id": h.id,
                "hook_name": h.name,
                "actions": h.actions or [],
            },
            queue="scheduled",
            account_id=h.account_id,
        )
        await job_repo.create(job)
        await hook_repo.update_schedule_timestamps(h.id, now, next_run)
    await db_session.commit()

    result = await db_session.execute(
        select(JobModel).where(JobModel.handler == "scheduled_hook")
    )
    jobs = list(result.scalars().all())
    assert len(jobs) == 1
    assert jobs[0].payload["hook_id"] == hook.id
    assert jobs[0].payload["hook_name"] == "My Schedule"
    assert len(jobs[0].payload["actions"]) == 1
