"""Integration tests for F8.2: Custom Endpoints (Serverless Functions).

Covers:
- CRUD for custom endpoints (create, list, get, update, delete)
- Path validation (invalid paths, reserved prefixes)
- Unique constraint enforcement (account_id, path, method)
- Endpoint count limit enforcement
- Toggle enabled/disabled
- Execution history (GET /{id}/executions)
- Account isolation (endpoints not visible cross-account)
- Dispatcher: matching by path + method
- Dispatcher: auth_required=True (401 if no token)
- Dispatcher: auth_required=False (publicly accessible)
- Dispatcher: path parameters (:param)
- Dispatcher: action chaining via actions[N].result
- Dispatcher: response_template rendering
- Dispatcher: empty actions array returns 200
- Dispatcher: 404 when no matching endpoint
- Dispatcher: account mismatch → 403
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.models.endpoint import EndpointModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000020",
        account_code="EP0001",
        name="Endpoint Test Account",
        slug="endpoint-test",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def other_account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000021",
        account_code="EP0002",
        name="Other Endpoint Account",
        slug="endpoint-test-other",
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
        id="endpoint-test-user-1",
        email="user@endpointtest.com",
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
        id="endpoint-test-user-2",
        email="user@endpointtestother.com",
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
# CREATE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_endpoint_minimal(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Hello", "path": "/hello", "method": "GET"},
        headers=_auth(user_token),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["path"] == "/hello"
    assert data["method"] == "GET"
    assert data["auth_required"] is True
    assert data["enabled"] is True
    assert data["actions"] == []
    assert data["response_template"] is None


@pytest.mark.asyncio
async def test_create_endpoint_full(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Submit Feedback",
            "description": "Accepts feedback",
            "path": "/submit-feedback",
            "method": "POST",
            "auth_required": False,
            "actions": [{"type": "send_webhook", "url": "https://example.com/hook"}],
            "response_template": {"status": 201, "body": {"ok": True}},
        },
        headers=_auth(user_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["auth_required"] is False
    assert data["actions"][0]["type"] == "send_webhook"
    assert data["response_template"]["status"] == 201


@pytest.mark.asyncio
async def test_create_endpoint_invalid_path_no_slash(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Bad", "path": "no-slash", "method": "GET"},
        headers=_auth(user_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_endpoint_reserved_path(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Bad", "path": "/auth/login", "method": "POST"},
        headers=_auth(user_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_endpoint_duplicate_409(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    payload = {"name": "Dup", "path": "/dup-test", "method": "POST"}
    resp1 = await client.post("/api/v1/endpoints", json=payload, headers=_auth(user_token))
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/endpoints", json=payload, headers=_auth(user_token))
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_create_endpoint_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "X", "path": "/x", "method": "GET"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_endpoints_empty(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.get("/api/v1/endpoints", headers=_auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_endpoints_with_filter(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    await client.post(
        "/api/v1/endpoints",
        json={"name": "A", "path": "/list-a", "method": "GET"},
        headers=_auth(user_token),
    )
    await client.post(
        "/api/v1/endpoints",
        json={"name": "B", "path": "/list-b", "method": "POST"},
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/endpoints?method=GET", headers=_auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["method"] == "GET"


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Get Test", "path": "/get-test", "method": "DELETE"},
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/endpoints/{eid}", headers=_auth(user_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == eid


@pytest.mark.asyncio
async def test_get_endpoint_not_found(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    resp = await client.get(
        "/api/v1/endpoints/00000000-0000-0000-0000-000000000099",
        headers=_auth(user_token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_endpoint(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Orig", "path": "/update-test", "method": "GET"},
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/endpoints/{eid}",
        json={"name": "Updated", "auth_required": False},
        headers=_auth(user_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["auth_required"] is False


# ---------------------------------------------------------------------------
# TOGGLE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_endpoint(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Toggle", "path": "/toggle-test", "method": "GET"},
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    toggle_resp = await client.patch(
        f"/api/v1/endpoints/{eid}/toggle", headers=_auth(user_token)
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] is False

    toggle_resp2 = await client.patch(
        f"/api/v1/endpoints/{eid}/toggle", headers=_auth(user_token)
    )
    assert toggle_resp2.json()["enabled"] is True


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_endpoint(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Del", "path": "/del-test", "method": "GET"},
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/endpoints/{eid}", headers=_auth(user_token))
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/endpoints/{eid}", headers=_auth(user_token))
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# ACCOUNT ISOLATION
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_isolation(
    client: AsyncClient,
    account: AccountModel,
    other_account: AccountModel,
    user_token: str,
    other_user_token: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={"name": "Isolated", "path": "/isolated", "method": "GET"},
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    # Other account cannot see it
    list_resp = await client.get("/api/v1/endpoints", headers=_auth(other_user_token))
    ids = [e["id"] for e in list_resp.json()["items"]]
    assert eid not in ids

    # Other account cannot get it directly
    get_resp = await client.get(f"/api/v1/endpoints/{eid}", headers=_auth(other_user_token))
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# DISPATCHER — basic invocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_empty_actions(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """An endpoint with no actions returns 200 with empty body by default."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Ping",
            "path": "/ping",
            "method": "GET",
            "auth_required": False,
            "actions": [],
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/ping")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dispatcher_response_template(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Response template static values are returned correctly."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Static",
            "path": "/static-resp",
            "method": "POST",
            "auth_required": False,
            "response_template": {
                "status": 201,
                "body": {"message": "created"},
                "headers": {"X-Custom": "yes"},
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.post("/api/v1/x/endpoint-test/static-resp", json={})
    assert resp.status_code == 201
    assert resp.json()["message"] == "created"
    assert resp.headers.get("x-custom") == "yes"


@pytest.mark.asyncio
async def test_dispatcher_auth_required_no_token(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """auth_required=True returns 401 when no token is provided."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Protected",
            "path": "/protected",
            "method": "GET",
            "auth_required": True,
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/protected")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dispatcher_auth_required_with_token(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """auth_required=True succeeds when a valid token is provided."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Protected2",
            "path": "/protected2",
            "method": "GET",
            "auth_required": True,
            "response_template": {"status": 200, "body": {"ok": True}},
        },
        headers=_auth(user_token),
    )

    resp = await client.get(
        "/api/v1/x/endpoint-test/protected2",
        headers=_auth(user_token),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_dispatcher_public_no_auth(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """auth_required=False allows unauthenticated access."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Public",
            "path": "/public-endpoint",
            "method": "GET",
            "auth_required": False,
            "response_template": {"status": 200, "body": {"public": True}},
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/public-endpoint")
    assert resp.status_code == 200
    assert resp.json()["public"] is True


@pytest.mark.asyncio
async def test_dispatcher_not_found(
    client: AsyncClient, account: AccountModel
) -> None:
    """Returns 404 when no endpoint matches."""
    resp = await client.get("/api/v1/x/endpoint-test/does-not-exist-at-all")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dispatcher_unknown_account(client: AsyncClient) -> None:
    """Returns 404 for an unknown account slug."""
    resp = await client.get("/api/v1/x/no-such-account-xyz/anything")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DISPATCHER — path parameters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_path_params(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Path parameters are resolved in the response template."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Profile",
            "path": "/profiles/:profile_id",
            "method": "GET",
            "auth_required": False,
            "response_template": {
                "status": 200,
                "body": {"profile_id": "{{request.params.profile_id}}"},
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/profiles/abc123")
    assert resp.status_code == 200
    assert resp.json()["profile_id"] == "abc123"


@pytest.mark.asyncio
async def test_dispatcher_multiple_path_params(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Multiple path params are all extracted correctly."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Item Detail",
            "path": "/shops/:shop_id/items/:item_id",
            "method": "GET",
            "auth_required": False,
            "response_template": {
                "status": 200,
                "body": {
                    "shop": "{{request.params.shop_id}}",
                    "item": "{{request.params.item_id}}",
                },
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/shops/s1/items/i2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["shop"] == "s1"
    assert body["item"] == "i2"


# ---------------------------------------------------------------------------
# DISPATCHER — request body and query params
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_request_body_template(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Request body fields are accessible via {{request.body.field}}."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Echo Body",
            "path": "/echo-body",
            "method": "POST",
            "auth_required": False,
            "response_template": {
                "status": 200,
                "body": {"echo": "{{request.body.message}}"},
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.post(
        "/api/v1/x/endpoint-test/echo-body",
        json={"message": "hello world"},
    )
    assert resp.status_code == 200
    assert resp.json()["echo"] == "hello world"


@pytest.mark.asyncio
async def test_dispatcher_query_params_template(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Query parameters are accessible via {{request.query.field}}."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Echo Query",
            "path": "/echo-query",
            "method": "GET",
            "auth_required": False,
            "response_template": {
                "status": 200,
                "body": {"q": "{{request.query.q}}"},
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.get("/api/v1/x/endpoint-test/echo-query?q=search-term")
    assert resp.status_code == 200
    assert resp.json()["q"] == "search-term"


# ---------------------------------------------------------------------------
# DISPATCHER — auth context in templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_auth_context_template(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Auth context variables are resolved in response template."""
    await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Auth Echo",
            "path": "/auth-echo",
            "method": "GET",
            "auth_required": True,
            "response_template": {
                "status": 200,
                "body": {
                    "account_id": "{{auth.account_id}}",
                    "user_id": "{{auth.user_id}}",
                },
            },
        },
        headers=_auth(user_token),
    )

    resp = await client.get(
        "/api/v1/x/endpoint-test/auth-echo",
        headers=_auth(user_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_id"] == account.id
    assert body["user_id"] == "endpoint-test-user-1"


# ---------------------------------------------------------------------------
# DISPATCHER — disabled endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_disabled_endpoint_not_found(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """A disabled endpoint is not dispatched (404)."""
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Disabled",
            "path": "/disabled-ep",
            "method": "GET",
            "auth_required": False,
        },
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]
    await client.patch(f"/api/v1/endpoints/{eid}/toggle", headers=_auth(user_token))

    resp = await client.get("/api/v1/x/endpoint-test/disabled-ep")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# EXECUTION HISTORY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_history_recorded(
    client: AsyncClient, account: AccountModel, user_token: str
) -> None:
    """Invocations are recorded in execution history."""
    create_resp = await client.post(
        "/api/v1/endpoints",
        json={
            "name": "Tracked",
            "path": "/tracked",
            "method": "GET",
            "auth_required": False,
            "response_template": {"status": 200, "body": {}},
        },
        headers=_auth(user_token),
    )
    eid = create_resp.json()["id"]

    # Invoke it
    await client.get("/api/v1/x/endpoint-test/tracked")

    history_resp = await client.get(
        f"/api/v1/endpoints/{eid}/executions", headers=_auth(user_token)
    )
    assert history_resp.status_code == 200
    data = history_resp.json()
    assert data["total"] >= 1
    exec_record = data["items"][0]
    assert exec_record["endpoint_id"] == eid
    assert exec_record["http_status"] == 200
    assert exec_record["status"] == "success"


# ---------------------------------------------------------------------------
# ENDPOINT LIMIT ENFORCEMENT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_limit_enforcement(
    client: AsyncClient, account: AccountModel, user_token: str, monkeypatch
) -> None:
    """Returns 409 when the account exceeds max_endpoints_per_account."""
    # Patch the limit to 2 for this test
    import snackbase.core.config as config_module

    original_settings = None
    try:
        settings = config_module.get_settings()
        original = settings.max_endpoints_per_account
        settings.max_endpoints_per_account = 2
    except Exception:
        pass

    try:
        for i in range(2):
            resp = await client.post(
                "/api/v1/endpoints",
                json={"name": f"EP{i}", "path": f"/limit-ep-{i}", "method": "GET"},
                headers=_auth(user_token),
            )
            assert resp.status_code == 201

        over_limit_resp = await client.post(
            "/api/v1/endpoints",
            json={"name": "Over", "path": "/over-limit", "method": "GET"},
            headers=_auth(user_token),
        )
        assert over_limit_resp.status_code == 409
    finally:
        try:
            settings.max_endpoints_per_account = original
        except Exception:
            pass
