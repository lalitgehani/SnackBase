"""Integration tests for Functions management + invoke APIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

HELLO = '''
from snackbase_fn import Request, Response

def handler(req: Request) -> Response:
    return Response.json({"ok": True, "echo": req.json})
'''

SECRET_HANDLER = '''
import os
from snackbase_fn import Response

def handler(req):
    return Response.json({"secret": os.environ.get("TEST_FN_SECRET")})
'''


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000030",
        account_code="FN0001",
        name="Functions Test Account",
        slug="fn-test",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def other_account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000031",
        account_code="FN0002",
        name="Other Functions Account",
        slug="fn-test-other",
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
        id="fn-test-admin-1",
        email="admin@fntest.com",
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


@pytest_asyncio.fixture
async def user_token(db_session: AsyncSession, account: AccountModel) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    user = UserModel(
        id="fn-test-user-1",
        email="user@fntest.com",
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


@pytest_asyncio.fixture
async def other_admin_token(db_session: AsyncSession, other_account: AccountModel) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    ).scalar_one()
    user = UserModel(
        id="fn-test-admin-2",
        email="admin@fntestother.com",
        account_id=other_account.id,
        password_hash="hashed",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user.id,
        account_id=other_account.id,
        email=user.email,
        role="admin",
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_list_get_function(
    client: AsyncClient, admin_token: str
) -> None:
    resp = await client.post(
        "/api/v1/functions",
        json={"name": "Hello", "slug": "hello", "auth_required": True},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slug"] == "hello"
    assert data["auth_required"] is True
    assert data["status"] == "ACTIVE"

    listed = await client.get("/api/v1/functions", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert any(i["slug"] == "hello" for i in listed.json()["items"])

    got = await client.get("/api/v1/functions/hello", headers=_auth(admin_token))
    assert got.status_code == 200
    assert got.json()["name"] == "Hello"


@pytest.mark.asyncio
async def test_cross_account_get_404(
    client: AsyncClient, admin_token: str, other_admin_token: str
) -> None:
    await client.post(
        "/api/v1/functions",
        json={"name": "Private", "slug": "private-fn"},
        headers=_auth(admin_token),
    )
    resp = await client.get("/api/v1/functions/private-fn", headers=_auth(other_admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_cannot_create(
    client: AsyncClient, user_token: str
) -> None:
    resp = await client.post(
        "/api/v1/functions",
        json={"name": "Nope", "slug": "nope"},
        headers=_auth(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_deploy_without_files_400(
    client: AsyncClient, admin_token: str
) -> None:
    await client.post(
        "/api/v1/functions",
        json={"name": "Empty", "slug": "empty-deploy"},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        "/api/v1/functions/empty-deploy/deploy",
        json={"files": {}},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_deploy_unpinned_dep_400(
    client: AsyncClient, admin_token: str
) -> None:
    await client.post(
        "/api/v1/functions",
        json={"name": "Deps", "slug": "bad-deps"},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        "/api/v1/functions/bad-deps/deploy",
        json={
            "files": {"handler.py": HELLO},
            "dependencies": ["openai"],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400
    assert "exact pin" in resp.text.lower() or "pin" in resp.text.lower()


@pytest.mark.asyncio
async def test_deploy_invoke_executions(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    create = await client.post(
        "/api/v1/functions",
        json={"name": "Hello", "slug": "hello-invoke", "auth_required": True},
        headers=_auth(admin_token),
    )
    assert create.status_code == 201, create.text

    deploy = await client.post(
        "/api/v1/functions/hello-invoke/deploy",
        json={"files": {"handler.py": HELLO}, "dependencies": []},
        headers=_auth(admin_token),
    )
    assert deploy.status_code == 200, deploy.text
    assert deploy.json()["version"]["version"] == 1

    invoke = await client.post(
        f"/api/v1/f/{account.slug}/hello-invoke",
        json={"name": "SnackBase"},
        headers=_auth(admin_token),
    )
    assert invoke.status_code == 200, invoke.text
    body = invoke.json()
    assert body["ok"] is True
    assert body["echo"] == {"name": "SnackBase"}
    exec_id = invoke.headers.get("x-function-execution-id")
    assert exec_id

    execs = await client.get(
        "/api/v1/functions/hello-invoke/executions",
        headers=_auth(admin_token),
    )
    assert execs.status_code == 200
    items = execs.json()["items"]
    assert len(items) >= 1
    assert items[0]["id"] == exec_id
    assert items[0]["status"] == "success"
    # Authorization must be redacted in request_data
    headers = (items[0].get("request_data") or {}).get("headers") or {}
    auth_val = headers.get("authorization") or headers.get("Authorization")
    if auth_val:
        assert "Bearer" not in str(auth_val) or "•" in str(auth_val)


@pytest.mark.asyncio
async def test_invoke_auth_matrix(
    client: AsyncClient,
    admin_token: str,
    other_admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Auth", "slug": "auth-req", "auth_required": True},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/auth-req/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )

    # Missing auth → 401
    r1 = await client.post(f"/api/v1/f/{account.slug}/auth-req", json={})
    assert r1.status_code == 401

    # Wrong account → 403
    r2 = await client.post(
        f"/api/v1/f/{account.slug}/auth-req",
        json={},
        headers=_auth(other_admin_token),
    )
    assert r2.status_code == 403

    # Public function
    await client.post(
        "/api/v1/functions",
        json={"name": "Public", "slug": "public-fn", "auth_required": False},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/public-fn/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )
    r3 = await client.post(
        f"/api/v1/f/{account.slug}/public-fn",
        json={"hi": 1},
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["ok"] is True


@pytest.mark.asyncio
async def test_soft_delete_and_throttle(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Life", "slug": "lifecycle", "auth_required": False},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/lifecycle/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )

    await client.patch(
        "/api/v1/functions/lifecycle",
        json={"status": "THROTTLED"},
        headers=_auth(admin_token),
    )
    r = await client.post(f"/api/v1/f/{account.slug}/lifecycle", json={})
    assert r.status_code == 429

    await client.patch(
        "/api/v1/functions/lifecycle",
        json={"status": "ACTIVE", "enabled": False},
        headers=_auth(admin_token),
    )
    r2 = await client.post(f"/api/v1/f/{account.slug}/lifecycle", json={})
    assert r2.status_code == 404

    await client.delete("/api/v1/functions/lifecycle", headers=_auth(admin_token))
    listed = await client.get("/api/v1/functions", headers=_auth(admin_token))
    assert all(i["slug"] != "lifecycle" for i in listed.json()["items"])


@pytest.mark.asyncio
async def test_function_secrets_inject(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    # Reject SNACKBASE_ prefix
    bad = await client.post(
        "/api/v1/function-secrets",
        json={"name": "SNACKBASE_URL", "value": "nope"},
        headers=_auth(admin_token),
    )
    assert bad.status_code == 422

    upsert = await client.post(
        "/api/v1/function-secrets",
        json={"name": "TEST_FN_SECRET", "value": "super-secret-value"},
        headers=_auth(admin_token),
    )
    assert upsert.status_code == 201, upsert.text
    listed = await client.get("/api/v1/function-secrets", headers=_auth(admin_token))
    assert listed.status_code == 200
    item = next(i for i in listed.json()["items"] if i["name"] == "TEST_FN_SECRET")
    assert "value" not in item
    assert "value_encrypted" not in item

    await client.post(
        "/api/v1/functions",
        json={"name": "Sec", "slug": "with-secret", "auth_required": False},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/with-secret/deploy",
        json={"files": {"handler.py": SECRET_HANDLER}},
        headers=_auth(admin_token),
    )
    inv = await client.post(f"/api/v1/f/{account.slug}/with-secret", json={})
    assert inv.status_code == 200, inv.text
    assert inv.json()["secret"] == "super-secret-value"


@pytest.mark.asyncio
async def test_options_cors(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Cors", "slug": "cors-fn", "auth_required": True},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/cors-fn/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )
    resp = await client.options(
        f"/api/v1/f/{account.slug}/cors-fn",
        headers={"Origin": "https://app.example.com"},
    )
    assert resp.status_code == 204
    assert "access-control-allow-origin" in {k.lower() for k in resp.headers.keys()}


@pytest.mark.asyncio
async def test_versions_rollback(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    v1 = '''
from snackbase_fn import Response
def handler(req):
    return Response.json({"v": 1})
'''
    v2 = '''
from snackbase_fn import Response
def handler(req):
    return Response.json({"v": 2})
'''
    await client.post(
        "/api/v1/functions",
        json={"name": "Vers", "slug": "vers", "auth_required": False},
        headers=_auth(admin_token),
    )
    d1 = await client.post(
        "/api/v1/functions/vers/deploy",
        json={"files": {"handler.py": v1}},
        headers=_auth(admin_token),
    )
    assert d1.status_code == 200, d1.text
    version1_id = d1.json()["version"]["id"]

    d2 = await client.post(
        "/api/v1/functions/vers/deploy",
        json={"files": {"handler.py": v2}},
        headers=_auth(admin_token),
    )
    assert d2.status_code == 200, d2.text

    r2 = await client.post(f"/api/v1/f/{account.slug}/vers", json={})
    assert r2.json()["v"] == 2

    act = await client.post(
        f"/api/v1/functions/vers/versions/{version1_id}/activate",
        headers=_auth(admin_token),
    )
    assert act.status_code == 200, act.text

    r1 = await client.post(f"/api/v1/f/{account.slug}/vers", json={})
    assert r1.json()["v"] == 1

    body = await client.get("/api/v1/functions/vers/body", headers=_auth(admin_token))
    assert body.status_code == 200
    assert "handler.py" in body.json()["files"]


@pytest.mark.asyncio
async def test_grants_and_stats(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Stats", "slug": "stats-fn", "auth_required": False},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/functions/stats-fn/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )
    await client.post(f"/api/v1/f/{account.slug}/stats-fn", json={})
    await client.post(f"/api/v1/f/{account.slug}/stats-fn", json={})

    stats = await client.get(
        "/api/v1/functions/stats-fn/stats?range=24h",
        headers=_auth(admin_token),
    )
    assert stats.status_code == 200
    assert stats.json()["total"] >= 2
    assert stats.json()["by_status"]["success"] >= 2

    grants = await client.patch(
        "/api/v1/functions/stats-fn/grants",
        json={"grants": ["records.read:todos"]},
        headers=_auth(admin_token),
    )
    assert grants.status_code == 200
    assert "records.read:todos" in grants.json()["grants"].get("capabilities", [])


BAD_SYNTAX = '''
def handler(req)
    return {"ok": True}
'''


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("slug", "path"),
    [
        ("path-abs", "/abs.py"),
        ("path-dotdot", "../outside.py"),
        ("path-nested-dotdot", "lib/../../outside.py"),
        ("path-backslash", "lib\\evil.py"),
        ("path-overlong", "a" * 256),
    ],
)
async def test_deploy_rejects_unsafe_paths(
    client: AsyncClient,
    admin_token: str,
    tmp_path,
    monkeypatch,
    slug: str,
    path: str,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs" / slug))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Path Guard", "slug": slug},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        f"/api/v1/functions/{slug}/deploy",
        json={"files": {path: HELLO, "handler.py": HELLO}, "entrypoint": "handler.py"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400, resp.text
    assert "Invalid source path" in resp.text or "path" in resp.text.lower()

    body = await client.get(f"/api/v1/functions/{slug}", headers=_auth(admin_token))
    assert body.json()["active_version_id"] is None
    env_root = tmp_path / "envs" / slug
    assert not env_root.exists() or not any(env_root.rglob("*"))


@pytest.mark.asyncio
async def test_deploy_rejects_empty_and_nul_paths(
    client: AsyncClient,
    admin_token: str,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Path Empty", "slug": "path-empty"},
        headers=_auth(admin_token),
    )
    empty = await client.post(
        "/api/v1/functions/path-empty/deploy",
        json={"files": {"": HELLO}, "entrypoint": ""},
        headers=_auth(admin_token),
    )
    assert empty.status_code == 400

    await client.post(
        "/api/v1/functions",
        json={"name": "Path Nul", "slug": "path-nul"},
        headers=_auth(admin_token),
    )
    nul_path = "has\0nul.py"
    nul = await client.post(
        "/api/v1/functions/path-nul/deploy",
        json={"files": {nul_path: HELLO, "handler.py": HELLO}, "entrypoint": "handler.py"},
        headers=_auth(admin_token),
    )
    # JSON may reject NUL; either request fails to encode or API returns 400
    assert nul.status_code in (400, 422) or nul.status_code >= 400


@pytest.mark.asyncio
async def test_deploy_accepts_nested_relative_path(
    client: AsyncClient,
    admin_token: str,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Nested", "slug": "nested-ok"},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        "/api/v1/functions/nested-ok/deploy",
        json={
            "entrypoint": "handler.py",
            "files": {
                "handler.py": HELLO,
                "lib/formatters.py": "def fmt(x):\n    return x\n",
            },
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"]["version"] == 1


@pytest.mark.asyncio
async def test_deploy_syntax_error_before_env_and_keeps_active_version(
    client: AsyncClient,
    admin_token: str,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    await client.post(
        "/api/v1/functions",
        json={"name": "Syntax", "slug": "syntax-fn"},
        headers=_auth(admin_token),
    )
    ok = await client.post(
        "/api/v1/functions/syntax-fn/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=_auth(admin_token),
    )
    assert ok.status_code == 200, ok.text
    active = ok.json()["function"]["active_version_id"]

    bad = await client.post(
        "/api/v1/functions/syntax-fn/deploy",
        json={"files": {"handler.py": BAD_SYNTAX}},
        headers=_auth(admin_token),
    )
    assert bad.status_code == 400, bad.text
    assert "handler.py" in bad.text
    assert "line" in bad.text.lower() or "Syntax error" in bad.text

    current = await client.get("/api/v1/functions/syntax-fn", headers=_auth(admin_token))
    assert current.json()["active_version_id"] == active
