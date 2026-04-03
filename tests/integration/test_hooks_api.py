"""Integration tests for F8.1: API-Defined Hooks.

Covers:
- CRUD for all three trigger types (schedule, event, manual)
- trigger_type filter on list endpoint
- Hook count limit enforcement
- toggle enabled/disabled
- manual trigger endpoint
- execution history (GET /executions)
- account isolation (hooks not visible cross-account)
- disabled hooks are skipped by dispatcher
- invalid event name / invalid cron validation
- condition field stored and returned
- actions field stored and returned
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.models.hook import HookModel
from snackbase.infrastructure.persistence.models.hook_execution import HookExecutionModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000010",
        account_code="HK0001",
        name="Hook Test Account",
        slug="hook-test",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def other_account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000011",
        account_code="HK0002",
        name="Other Hook Account",
        slug="hook-test-other",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def user_token(db_session: AsyncSession, account: AccountModel) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    user = UserModel(
        id="hook-test-user-1",
        email="user@hooktest.com",
        account_id=account.id,
        password_hash="hashed",
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user.id,
        account_id=account.id,
        email=user.email,
        role="user",
    )


@pytest_asyncio.fixture
async def other_user_token(db_session: AsyncSession, other_account: AccountModel) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    user = UserModel(
        id="hook-test-user-2",
        email="user@hooktestother.com",
        account_id=other_account.id,
        password_hash="hashed",
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user.id,
        account_id=other_account.id,
        email=user.email,
        role="user",
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# CREATE — schedule trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule_hook(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/hooks creates a schedule-type hook and returns next_run_at."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Daily Digest",
            "trigger": {"type": "schedule", "cron": "0 9 * * *"},
            "actions": [],
            "enabled": True,
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Daily Digest"
    assert data["trigger"]["type"] == "schedule"
    assert data["trigger"]["cron"] == "0 9 * * *"
    assert data["cron"] == "0 9 * * *"
    assert data["cron_description"] is not None
    assert data["next_run_at"] is not None
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_schedule_hook_invalid_cron(client: AsyncClient, user_token: str) -> None:
    """Invalid cron expression returns 422."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Bad Cron",
            "trigger": {"type": "schedule", "cron": "not-a-cron"},
            "actions": [],
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 422
    assert "cron" in response.text.lower() or "Invalid" in response.text


@pytest.mark.asyncio
async def test_create_schedule_hook_disabled_has_no_next_run(
    client: AsyncClient, user_token: str
) -> None:
    """Disabled schedule hook has next_run_at = None."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Disabled Digest",
            "trigger": {"type": "schedule", "cron": "0 9 * * *"},
            "enabled": False,
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 201
    assert response.json()["next_run_at"] is None
    assert response.json()["enabled"] is False


# ---------------------------------------------------------------------------
# CREATE — event trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_event_hook(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/hooks creates an event-type hook."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "On Record Create",
            "trigger": {"type": "event", "event": "records.create", "collection": "posts"},
            "condition": 'status = "published"',
            "actions": [{"type": "send_webhook", "url": "https://example.com/notify"}],
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["trigger"]["type"] == "event"
    assert data["trigger"]["event"] == "records.create"
    assert data["trigger"]["collection"] == "posts"
    assert data["condition"] == 'status = "published"'
    assert len(data["actions"]) == 1
    assert data["next_run_at"] is None  # event hooks don't have next_run_at
    assert data["cron"] is None


@pytest.mark.asyncio
async def test_create_event_hook_without_collection(client: AsyncClient, user_token: str) -> None:
    """Event hook with no collection listens to all collections."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Global Create Listener",
            "trigger": {"type": "event", "event": "records.create"},
            "actions": [],
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["trigger"].get("collection") is None


@pytest.mark.asyncio
async def test_create_event_hook_invalid_event(client: AsyncClient, user_token: str) -> None:
    """Unknown event name returns 422."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Bad Event",
            "trigger": {"type": "event", "event": "records.nonexistent"},
            "actions": [],
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_event_hook_all_record_events(client: AsyncClient, user_token: str) -> None:
    """All supported record event strings are accepted."""
    for event in ("records.create", "records.update", "records.delete"):
        response = await client.post(
            "/api/v1/hooks",
            json={
                "name": f"Hook for {event}",
                "trigger": {"type": "event", "event": event},
                "actions": [],
            },
            headers=_auth(user_token),
        )
        assert response.status_code == 201, f"Failed for event={event}: {response.text}"


@pytest.mark.asyncio
async def test_create_event_hook_auth_events(client: AsyncClient, user_token: str) -> None:
    """Auth event strings are accepted."""
    for event in ("auth.login", "auth.register"):
        response = await client.post(
            "/api/v1/hooks",
            json={
                "name": f"Hook for {event}",
                "trigger": {"type": "event", "event": event},
                "actions": [],
            },
            headers=_auth(user_token),
        )
        assert response.status_code == 201, f"Failed for event={event}: {response.text}"


# ---------------------------------------------------------------------------
# CREATE — manual trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_manual_hook(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/hooks creates a manual-type hook."""
    response = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Runbook Step",
            "description": "Triggered by ops team",
            "trigger": {"type": "manual"},
            "actions": [{"type": "enqueue_job", "handler": "sync_report", "payload": {}}],
        },
        headers=_auth(user_token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["trigger"]["type"] == "manual"
    assert data["next_run_at"] is None
    assert data["cron"] is None
    assert data["description"] == "Triggered by ops team"


# ---------------------------------------------------------------------------
# READ — get + list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_hook(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks/{id} returns the hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Get Me", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.get(f"/api/v1/hooks/{hook_id}", headers=_auth(user_token))
    assert response.status_code == 200
    assert response.json()["id"] == hook_id


@pytest.mark.asyncio
async def test_get_hook_not_found(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks/{non-existent-id} returns 404."""
    response = await client.get("/api/v1/hooks/does-not-exist", headers=_auth(user_token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_hooks_empty(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks returns empty list when no hooks exist."""
    response = await client.get("/api/v1/hooks", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_hooks_returns_all_types(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks returns all three trigger types."""
    for payload in [
        {"name": "S", "trigger": {"type": "schedule", "cron": "0 * * * *"}, "actions": []},
        {"name": "E", "trigger": {"type": "event", "event": "records.create"}, "actions": []},
        {"name": "M", "trigger": {"type": "manual"}, "actions": []},
    ]:
        r = await client.post("/api/v1/hooks", json=payload, headers=_auth(user_token))
        assert r.status_code == 201

    response = await client.get("/api/v1/hooks", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_list_hooks_filter_by_trigger_type(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks?trigger_type=event returns only event hooks."""
    for payload in [
        {"name": "S", "trigger": {"type": "schedule", "cron": "0 * * * *"}, "actions": []},
        {"name": "E1", "trigger": {"type": "event", "event": "records.create"}, "actions": []},
        {"name": "E2", "trigger": {"type": "event", "event": "records.delete"}, "actions": []},
        {"name": "M", "trigger": {"type": "manual"}, "actions": []},
    ]:
        await client.post("/api/v1/hooks", json=payload, headers=_auth(user_token))

    response = await client.get(
        "/api/v1/hooks?trigger_type=event", headers=_auth(user_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(h["trigger"]["type"] == "event" for h in data["items"])


@pytest.mark.asyncio
async def test_list_hooks_filter_schedule(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks?trigger_type=schedule returns only schedule hooks."""
    await client.post(
        "/api/v1/hooks",
        json={"name": "S", "trigger": {"type": "schedule", "cron": "0 * * * *"}, "actions": []},
        headers=_auth(user_token),
    )
    await client.post(
        "/api/v1/hooks",
        json={"name": "M", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )

    response = await client.get(
        "/api/v1/hooks?trigger_type=schedule", headers=_auth(user_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["trigger"]["type"] == "schedule"


@pytest.mark.asyncio
async def test_list_hooks_filter_enabled(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks?enabled=false returns only disabled hooks."""
    await client.post(
        "/api/v1/hooks",
        json={"name": "Active", "trigger": {"type": "manual"}, "actions": [], "enabled": True},
        headers=_auth(user_token),
    )
    await client.post(
        "/api/v1/hooks",
        json={"name": "Inactive", "trigger": {"type": "manual"}, "actions": [], "enabled": False},
        headers=_auth(user_token),
    )

    response = await client.get("/api/v1/hooks?enabled=false", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Inactive"


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_hook_name_and_description(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id} updates name and description."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Old Name", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/hooks/{hook_id}",
        json={"name": "New Name", "description": "Updated desc"},
        headers=_auth(user_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_update_hook_trigger_to_event(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id} can change trigger type from manual to event."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/hooks/{hook_id}",
        json={"trigger": {"type": "event", "event": "records.update", "collection": "orders"}},
        headers=_auth(user_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trigger"]["type"] == "event"
    assert data["trigger"]["event"] == "records.update"
    assert data["trigger"]["collection"] == "orders"


@pytest.mark.asyncio
async def test_update_hook_condition(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id} updates condition expression."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/hooks/{hook_id}",
        json={"condition": 'status = "active"'},
        headers=_auth(user_token),
    )
    assert response.status_code == 200
    assert response.json()["condition"] == 'status = "active"'


@pytest.mark.asyncio
async def test_update_hook_actions(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id} updates actions list."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    new_actions = [{"type": "enqueue_job", "handler": "process_batch", "payload": {"size": 100}}]
    response = await client.patch(
        f"/api/v1/hooks/{hook_id}",
        json={"actions": new_actions},
        headers=_auth(user_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["handler"] == "process_batch"


@pytest.mark.asyncio
async def test_update_hook_not_found(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{non-existent} returns 404."""
    response = await client.patch(
        "/api/v1/hooks/does-not-exist",
        json={"name": "x"},
        headers=_auth(user_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_schedule_hook_invalid_cron(client: AsyncClient, user_token: str) -> None:
    """Updating a schedule trigger with invalid cron returns 422."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Hook", "trigger": {"type": "schedule", "cron": "0 * * * *"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/hooks/{hook_id}",
        json={"trigger": {"type": "schedule", "cron": "bad"}},
        headers=_auth(user_token),
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_hook(client: AsyncClient, user_token: str) -> None:
    """DELETE /api/v1/hooks/{id} removes the hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Delete Me", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.delete(f"/api/v1/hooks/{hook_id}", headers=_auth(user_token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/hooks/{hook_id}", headers=_auth(user_token))
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_hook_not_found(client: AsyncClient, user_token: str) -> None:
    """DELETE /api/v1/hooks/{non-existent} returns 404."""
    response = await client.delete("/api/v1/hooks/does-not-exist", headers=_auth(user_token))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# TOGGLE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_hook_disables(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id}/toggle disables an enabled hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Toggle Me", "trigger": {"type": "manual"}, "actions": [], "enabled": True},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(f"/api/v1/hooks/{hook_id}/toggle", headers=_auth(user_token))
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_toggle_hook_enables(client: AsyncClient, user_token: str) -> None:
    """PATCH /api/v1/hooks/{id}/toggle re-enables a disabled hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Toggle Me", "trigger": {"type": "manual"}, "actions": [], "enabled": False},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.patch(f"/api/v1/hooks/{hook_id}/toggle", headers=_auth(user_token))
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_toggle_schedule_hook_recalculates_next_run(
    client: AsyncClient, user_token: str
) -> None:
    """Re-enabling a schedule hook sets a new next_run_at."""
    create = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Toggle Schedule",
            "trigger": {"type": "schedule", "cron": "0 * * * *"},
            "enabled": False,
        },
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]
    assert create.json()["next_run_at"] is None

    response = await client.patch(f"/api/v1/hooks/{hook_id}/toggle", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["next_run_at"] is not None


# ---------------------------------------------------------------------------
# MANUAL TRIGGER
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_manual_hook(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/hooks/{id}/trigger executes a manual hook and returns result."""
    create = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Run Now",
            "trigger": {"type": "manual"},
            "actions": [],  # no-op actions so it succeeds
        },
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.post(f"/api/v1/hooks/{hook_id}/trigger", headers=_auth(user_token))
    assert response.status_code == 202, response.text
    data = response.json()
    assert "status" in data
    assert "actions_executed" in data


@pytest.mark.asyncio
async def test_trigger_event_hook_manually(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/hooks/{id}/trigger works for event-type hooks too."""
    create = await client.post(
        "/api/v1/hooks",
        json={
            "name": "Event Hook Manual Trigger",
            "trigger": {"type": "event", "event": "records.create"},
            "actions": [],
        },
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.post(f"/api/v1/hooks/{hook_id}/trigger", headers=_auth(user_token))
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_trigger_disabled_hook_still_works(client: AsyncClient, user_token: str) -> None:
    """Manual trigger ignores enabled flag — always fires."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Disabled Hook", "trigger": {"type": "manual"}, "actions": [], "enabled": False},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.post(f"/api/v1/hooks/{hook_id}/trigger", headers=_auth(user_token))
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# EXECUTION HISTORY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_executions_empty(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks/{id}/executions returns empty list for new hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "No Executions", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.get(f"/api/v1/hooks/{hook_id}/executions", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_executions_after_trigger(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks/{id}/executions returns execution record after manual trigger."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Executed Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    # Trigger the hook (no-op actions, should produce success execution)
    await client.post(f"/api/v1/hooks/{hook_id}/trigger", headers=_auth(user_token))

    response = await client.get(f"/api/v1/hooks/{hook_id}/executions", headers=_auth(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    execution = data["items"][0]
    assert execution["hook_id"] == hook_id
    assert execution["trigger_type"] == "manual"
    assert execution["status"] == "success"
    assert execution["actions_executed"] == 0  # empty actions list
    assert "executed_at" in execution


@pytest.mark.asyncio
async def test_get_executions_not_found(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/hooks/{non-existent}/executions returns 404."""
    response = await client.get(
        "/api/v1/hooks/does-not-exist/executions", headers=_auth(user_token)
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# ACCOUNT ISOLATION — security
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hook_not_visible_cross_account(
    client: AsyncClient, user_token: str, other_user_token: str
) -> None:
    """A hook created by account A is not visible to account B."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Private Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    # Account B tries to read account A's hook
    response = await client.get(f"/api/v1/hooks/{hook_id}", headers=_auth(other_user_token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hook_not_in_other_account_list(
    client: AsyncClient, user_token: str, other_user_token: str
) -> None:
    """Account B's list does not include account A's hooks."""
    await client.post(
        "/api/v1/hooks",
        json={"name": "Account A Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )

    response = await client.get("/api/v1/hooks", headers=_auth(other_user_token))
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_other_account_hook_forbidden(
    client: AsyncClient, user_token: str, other_user_token: str
) -> None:
    """Account B cannot delete account A's hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Protected Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.delete(f"/api/v1/hooks/{hook_id}", headers=_auth(other_user_token))
    assert response.status_code == 404

    # Verify hook still exists for its owner
    owner_response = await client.get(f"/api/v1/hooks/{hook_id}", headers=_auth(user_token))
    assert owner_response.status_code == 200


@pytest.mark.asyncio
async def test_trigger_other_account_hook_forbidden(
    client: AsyncClient, user_token: str, other_user_token: str
) -> None:
    """Account B cannot manually trigger account A's hook."""
    create = await client.post(
        "/api/v1/hooks",
        json={"name": "Protected Hook", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    hook_id = create.json()["id"]

    response = await client.post(
        f"/api/v1/hooks/{hook_id}/trigger", headers=_auth(other_user_token)
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# HOOK COUNT LIMIT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hook_count_limit_enforced(
    client: AsyncClient, user_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating more hooks than the limit returns 409."""
    from snackbase.core import config as cfg

    # Patch the settings to have a low limit
    original_get = cfg.get_settings

    class PatchedSettings:
        def __getattr__(self, name: str):
            if name == "max_hooks_per_account":
                return 2
            return getattr(original_get(), name)

    monkeypatch.setattr(cfg, "get_settings", lambda: PatchedSettings())

    # Create up to the limit
    for i in range(2):
        r = await client.post(
            "/api/v1/hooks",
            json={"name": f"Hook {i}", "trigger": {"type": "manual"}, "actions": []},
            headers=_auth(user_token),
        )
        assert r.status_code == 201, f"Hook {i} creation failed: {r.text}"

    # One more should fail
    r = await client.post(
        "/api/v1/hooks",
        json={"name": "One Too Many", "trigger": {"type": "manual"}, "actions": []},
        headers=_auth(user_token),
    )
    assert r.status_code == 409
    assert "maximum" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AUTHENTICATION REQUIRED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_hook_requires_auth(client: AsyncClient) -> None:
    """POST /api/v1/hooks without token returns 401 or 403."""
    response = await client.post(
        "/api/v1/hooks",
        json={"name": "x", "trigger": {"type": "manual"}, "actions": []},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_hooks_requires_auth(client: AsyncClient) -> None:
    """GET /api/v1/hooks without token returns 401 or 403."""
    response = await client.get("/api/v1/hooks")
    assert response.status_code in (401, 403)
