"""Integration test for invoke_function automation action."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.functions.invoke_action import execute_invoke_function
from snackbase.infrastructure.persistence.database import get_db_manager
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

HELLO = '''
from snackbase_fn import Response

def handler(req):
    return Response.json({"from_action": True, "payload": req.json})
'''


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000040",
        account_code="FN0040",
        name="Action Test",
        slug="fn-action",
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
        id="fn-action-admin",
        email="action@fntest.com",
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


@pytest.mark.asyncio
async def test_invoke_function_action(
    client: AsyncClient,
    admin_token: str,
    account: AccountModel,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNACKBASE_FUNCTION_ENV_BASE_PATH", str(tmp_path / "envs"))
    from snackbase.core.config import get_settings

    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.post(
        "/api/v1/functions",
        json={"name": "Action", "slug": "action-fn", "auth_required": False},
        headers=headers,
    )
    deploy = await client.post(
        "/api/v1/functions/action-fn/deploy",
        json={"files": {"handler.py": HELLO}},
        headers=headers,
    )
    assert deploy.status_code == 200, deploy.text

    result = await execute_invoke_function(
        {"slug": "action-fn", "payload": {"x": 1}},
        session_factory=get_db_manager().session,
        account_id=account.id,
    )
    assert result["status"] == "success"
    assert result["body"]["from_action"] is True
    assert result["body"]["payload"] == {"x": 1}
    assert result["execution_id"]
