import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.security.reporter.html_reporter import HTMLReporter
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.auth.jwt_service import jwt_service


class AttackClient:
    """A wrapper around AsyncClient that logs all requests to the HTMLReporter."""

    def __init__(self, client: AsyncClient, reporter: HTMLReporter):
        self.client = client
        self.reporter = reporter

    async def _make_request(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        description: str = "",
        **kwargs
    ) -> Any:
        response = await self.client.request(method, url, json=json, **kwargs)

        status = "PASSED"
        # Try to parse response body
        try:
            response_body = response.json()
        except Exception:
            response_body = response.text

        self.reporter.log_request(
            description=description or f"{method} {url}",
            method=method,
            url=url,
            headers=dict(kwargs.get("headers", {})),
            body=json,
            response_status=response.status_code,
            response_body=response_body,
            status=status
        )
        return response

    async def get(self, url: str, description: str = "", **kwargs) -> Any:
        return await self._make_request("GET", url, description=description, **kwargs)

    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("POST", url, json=json, description=description, **kwargs)

    async def put(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PUT", url, json=json, description=description, **kwargs)

    async def delete(self, url: str, description: str = "", **kwargs) -> Any:
        return await self._make_request("DELETE", url, description=description, **kwargs)

    async def patch(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PATCH", url, json=json, description=description, **kwargs)


@pytest.fixture(scope="session")
def security_reporter():
    """Shared reporter for the entire security test session."""
    reporter = HTMLReporter(suite_name="Security Audit Suite")
    yield reporter
    # Generate the single consolidated report at the end of the session
    report_path = reporter.generate()
    print(f"\nConsolidated security report generated: {report_path}")


@pytest.fixture(autouse=True)
def setup_security_test_section(request, security_reporter):
    """Automatically starts a new section in the reporter for each test."""
    # Only for security tests
    if "security" in request.node.fspath.strpath:
        security_reporter.start_section(request.node.name)
    yield


@pytest.fixture
def html_reporter(security_reporter):
    """Provide the shared reporter instance to tests."""
    return security_reporter


@pytest_asyncio.fixture
async def attack_client(client: AsyncClient, html_reporter: HTMLReporter) -> AttackClient:
    """An HTTP client that logs all requests to the security reporter."""
    return AttackClient(client, html_reporter)


@pytest_asyncio.fixture
async def security_test_data(db_session: AsyncSession) -> Dict[str, Any]:
    """Create test accounts and users for security testing.
    
    Provides:
    - account_a: Account A (AB1111)
    - account_b: Account B (AB2222) 
    - user_a: User in Account A (admin role)
    - user_b: User in Account B (user role)
    - user_a_token: Token for User A
    - user_b_token: Token for User B
    """
    # 1. Look up Roles
    result_admin = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result_admin.scalar_one()
    
    result_user = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result_user.scalar_one()
    
    # 2. Create Accounts
    account_a = AccountModel(
        id=str(uuid.uuid4()),
        account_code="AB1111",
        name="Account A",
        slug=f"account-a-{uuid.uuid4().hex[:6]}"
    )
    account_b = AccountModel(
        id=str(uuid.uuid4()),
        account_code="AB2222",
        name="Account B",
        slug=f"account-b-{uuid.uuid4().hex[:6]}"
    )
    db_session.add_all([account_a, account_b])
    await db_session.flush()

    # 3. Create Users
    user_a = UserModel(
        id=str(uuid.uuid4()),
        email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_a.id,
        password_hash="hashed_secret",
        role_id=admin_role.id,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user_b = UserModel(
        id=str(uuid.uuid4()),
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_b.id,
        password_hash="hashed_secret",
        role_id=user_role.id,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # 4. Generate Tokens
    token_a = jwt_service.create_access_token(
        user_id=user_a.id,
        account_id=user_a.account_id,
        email=user_a.email,
        role="admin"
    )
    token_b = jwt_service.create_access_token(
        user_id=user_b.id,
        account_id=user_b.account_id,
        email=user_b.email,
        role="user"
    )

    return {
        "account_a": account_a,
        "account_b": account_b,
        "user_a": user_a,
        "user_b": user_b,
        "user_a_token": token_a,
        "user_b_token": token_b
    }
