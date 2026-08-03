"""Integration tests for SSRF deny, admin grants, nested budget, streaming."""

from __future__ import annotations

import socket
import threading
import time
from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
import uvicorn
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.functions.nested_budget import reset_nested_invoke_budget
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

SSRF_HANDLER = '''
import httpx
from snackbase_fn import Response
from snackbase_fn.egress import EgressDeniedError

def handler(req):
    try:
        httpx.get("http://127.0.0.1/", timeout=2.0)
        return Response.json({"ssrf": "allowed"})
    except EgressDeniedError as exc:
        return Response.json({
            "ssrf": "denied",
            "error": str(exc),
            "error_type": "EgressDeniedError",
        }, status=200)
    except Exception as exc:
        return Response.json({
            "ssrf": "other",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }, status=200)
'''

METADATA_HANDLER = '''
import httpx
from snackbase_fn import Response
from snackbase_fn.egress import EgressDeniedError

def handler(req):
    try:
        httpx.get("http://169.254.169.254/latest/meta-data/", timeout=2.0)
        return Response.json({"ssrf": "allowed"})
    except EgressDeniedError as exc:
        return Response.json({
            "ssrf": "denied",
            "error": str(exc),
            "error_type": "EgressDeniedError",
        }, status=200)
    except Exception as exc:
        return Response.json({
            "ssrf": "other",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }, status=200)
'''

ADMIN_GRANT_HANDLER = '''
from snackbase_fn import Response, get_admin_client

def handler(req):
    client = get_admin_client()
    try:
        client.get("/api/v1/records/todos")
        return Response.json({"ok": True})
    except PermissionError as exc:
        return Response.json({"ok": False, "error": str(exc)}, status=403)
    except Exception as exc:
        return Response.json({"ok": False, "error": str(exc)}, status=500)
'''

STREAM_HANDLER = '''
from snackbase_fn import Response

def handler(req):
    def gen():
        yield b"data: chunk-one\\n\\n"
        yield b"data: chunk-two\\n\\n"
        yield b"data: done\\n\\n"
    return Response.stream_response(gen(), media_type="text/event-stream")
'''

# Real recursive self-invoke via get_client() — relies on X-Function-Depth propagation
RECURSIVE_HANDLER = '''
import os
from snackbase_fn import Response, get_client

def handler(req):
    depth = int(os.environ.get("FN_DEPTH", "0"))
    account_slug = os.environ.get("FN_ACCOUNT_SLUG", "")
    slug = os.environ.get("FN_SLUG", "")
    client = get_client()
    try:
        r = client.post(f"/api/v1/f/{account_slug}/{slug}", json={"from_depth": depth})
        body = None
        try:
            body = r.json()
        except Exception:
            body = {"raw": (r.text or "")[:300]}
        if r.status_code == 429:
            return Response.json(
                {
                    "detail": "Nested function invoke budget exceeded",
                    "depth": depth,
                    "child_status": 429,
                    "child": body,
                },
                status=429,
            )
        return Response.json({
            "depth": depth,
            "child_status": r.status_code,
            "child": body,
        })
    except Exception as exc:
        return Response.json({"depth": depth, "error": str(exc)}, status=500)
'''


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000050",
        account_code="FN0050",
        name="Sec Path Account",
        slug="fn-sec",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def admin_token(db_session: AsyncSession, account: AccountModel) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    ).scalar_one()
    user = UserModel(
        id="fn-sec-admin",
        email="sec@fntest.com",
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
        role="admin",
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_deploy(
    client: AsyncClient,
    token: str,
    slug: str,
    handler: str,
    *,
    auth_required: bool = False,
    grants: list[str] | None = None,
) -> None:
    r = await client.post(
        "/api/v1/functions",
        json={"name": slug, "slug": slug, "auth_required": auth_required},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    d = await client.post(
        f"/api/v1/functions/{slug}/deploy",
        json={"files": {"handler.py": handler}},
        headers=_auth(token),
    )
    assert d.status_code == 200, d.text
    if grants is not None:
        g = await client.patch(
            f"/api/v1/functions/{slug}/grants",
            json={"grants": grants},
            headers=_auth(token),
        )
        assert g.status_code == 200, g.text


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def live_server(client: AsyncClient) -> str:
    """Run the test app (with DB overrides) on a real TCP port for subprocess self-invoke."""
    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
        # Skip app lifespan so this fixture does not migrate the developer
        # sb_data database; tests already provide DB via dependency overrides.
        lifespan="off",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    # Wait until accepting connections
    for _ in range(100):
        try:
            httpx.get(f"{base}/api/v1", timeout=0.2)
            break
        except Exception:
            time.sleep(0.05)
    else:
        server.should_exit = True
        raise RuntimeError("live_server failed to start")
    yield base
    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.asyncio
async def test_ssrf_denies_loopback_from_handler(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await _create_deploy(client, admin_token, "ssrf-loop", SSRF_HANDLER)
    inv = await client.post(f"/api/v1/f/{account.slug}/ssrf-loop", json={})
    assert inv.status_code == 200, inv.text
    body = inv.json()
    assert body["ssrf"] == "denied", body
    assert body.get("error_type") == "EgressDeniedError", body
    err = (body.get("error") or "").lower()
    assert any(
        t in err for t in ("block", "private", "loopback", "127.0.0.1", "egress", "denied")
    ), body


@pytest.mark.asyncio
async def test_ssrf_denies_metadata_ip(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await _create_deploy(client, admin_token, "ssrf-meta", METADATA_HANDLER)
    inv = await client.post(f"/api/v1/f/{account.slug}/ssrf-meta", json={})
    assert inv.status_code == 200, inv.text
    body = inv.json()
    assert body["ssrf"] == "denied", body
    assert body.get("error_type") == "EgressDeniedError", body


@pytest.mark.asyncio
async def test_admin_grants_deny_by_default_and_allow_with_grant(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await _create_deploy(
        client, admin_token, "grant-deny", ADMIN_GRANT_HANDLER, grants=[]
    )
    denied = await client.post(f"/api/v1/f/{account.slug}/grant-deny", json={})
    assert denied.status_code == 403, denied.text
    assert denied.json()["ok"] is False
    assert "grant" in denied.json()["error"].lower()

    await _create_deploy(
        client,
        admin_token,
        "grant-allow",
        ADMIN_GRANT_HANDLER,
        grants=["records.read:todos"],
    )
    allowed = await client.post(f"/api/v1/f/{account.slug}/grant-allow", json={})
    body = allowed.json()
    if allowed.status_code == 403 and "grant" in str(body.get("error", "")).lower():
        pytest.fail(f"grant should allow records.read:todos, got {body}")


@pytest.mark.asyncio
async def test_recursive_self_invoke_hits_nested_budget(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
    live_server: str,
) -> None:
    """Handler POSTs /api/v1/f/... to itself; depth headers propagate until 429."""
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    monkeypatch.setenv("SNACKBASE_FUNCTION_NESTED_INVOKE_LIMIT_PER_MINUTE", "3")
    from snackbase.core.config import get_settings

    get_settings.cache_clear()
    reset_nested_invoke_budget()

    await _create_deploy(
        client,
        admin_token,
        "recur-fn",
        RECURSIVE_HANDLER,
        auth_required=False,
    )

    # Invoke via live TCP server so child subprocess can HTTP self-invoke
    async with httpx.AsyncClient(base_url=live_server, timeout=60.0) as live:
        inv = await live.post(f"/api/v1/f/{account.slug}/recur-fn", json={})

    assert inv.status_code == 429, inv.text
    body = inv.json()
    assert "budget" in str(body.get("detail", "")).lower() or body.get("child_status") == 429 or inv.status_code == 429


@pytest.mark.asyncio
async def test_streaming_response_chunks(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await _create_deploy(client, admin_token, "stream-fn", STREAM_HANDLER)
    inv = await client.post(f"/api/v1/f/{account.slug}/stream-fn", json={})
    assert inv.status_code == 200, inv.text
    text = inv.text
    assert "chunk-one" in text
    assert "chunk-two" in text
    assert "done" in text
    assert inv.headers.get("x-function-execution-id")

    execs = await client.get(
        "/api/v1/functions/stream-fn/executions",
        headers=_auth(admin_token),
    )
    assert execs.status_code == 200
    item = execs.json()["items"][0]
    assert item["status"] == "success"
    rb = item.get("response_body")
    assert rb is not None
    if isinstance(rb, dict):
        assert rb.get("streaming") is True
