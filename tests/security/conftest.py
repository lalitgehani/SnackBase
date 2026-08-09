import shutil
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from tests.security.reporter.html_reporter import HTMLReporter

SECURITY_SUITE_ROOT = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    """Apply the ``security`` marker to every test in ``tests/security/``.

    Applying it here (rather than a ``pytestmark`` line in each module) means
    a new security module is selected by ``-m security`` automatically and
    cannot be forgotten. See ``tests/security/README.md``.
    """
    for item in items:
        try:
            item_path = Path(str(item.fspath))
        except Exception:
            continue
        if SECURITY_SUITE_ROOT in item_path.parents:
            item.add_marker(pytest.mark.security)


_REPORTER: HTMLReporter | None = None


def _get_reporter() -> HTMLReporter:
    """Return the process-wide reporter.

    Held as a module global rather than only as a fixture because
    ``pytest_runtest_makereport`` is a hook and cannot request fixtures.
    """
    global _REPORTER
    if _REPORTER is None:
        _REPORTER = HTMLReporter(suite_name="Security Audit Suite")
    return _REPORTER


def _skip_reason(report: Any) -> str:
    """Extract the human-readable reason from a skip report."""
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return str(longrepr or "")


def _is_security_item(item: Any) -> bool:
    try:
        return SECURITY_SUITE_ROOT in Path(str(item.fspath)).parents
    except Exception:
        return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record each security test's real outcome into the HTML report.

    Without this the report only ever showed the hardcoded "PASSED" that
    ``start_section`` writes, so a test guarding a *confirmed* vulnerability
    was rendered as a pass. For a security artefact that is worse than no
    report at all.

    The mapping is deliberately not pytest's: an ``xfail`` here means "the
    secure behaviour asserted by this test does not hold", i.e. a confirmed
    finding, and an unexpected pass means the fix has landed and the marker is
    now stale.
    """
    outcome = yield
    report = outcome.get_result()

    if not _is_security_item(item):
        return

    reporter = _get_reporter()

    if report.when == "setup":
        if report.failed:
            reporter.record_outcome(item.nodeid, "ERROR", detail="fixture setup failed")
        elif report.skipped:
            # `pytest.mark.skip` and skips raised from a fixture never reach the
            # call phase, so they must be recorded here or they render blank.
            reporter.record_outcome(
                item.nodeid, "SKIPPED", detail=_skip_reason(report)
            )
        return

    if report.when != "call":
        return

    wasxfail = getattr(report, "wasxfail", None)
    longrepr = report.longrepr if isinstance(report.longrepr, str) else ""

    if report.skipped and wasxfail is not None:
        status, detail = "VULNERABLE", wasxfail
    elif wasxfail is not None or "XPASS(strict)" in longrepr:
        # The asserted secure behaviour now holds — the xfail marker is stale.
        status, detail = "FIXED", wasxfail or longrepr
    elif report.skipped:
        status, detail = "SKIPPED", longrepr
    elif report.failed:
        status, detail = "FAILED", str(report.longrepr)[:2000]
    else:
        status, detail = "PASSED", ""

    reporter.record_outcome(
        item.nodeid,
        status,
        detail=detail,
        duration=getattr(report, "duration", 0.0),
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class AttackClient:
    """A wrapper around AsyncClient that logs all requests to the HTMLReporter."""

    def __init__(self, client: AsyncClient, reporter: HTMLReporter):
        self.client = client
        self.reporter = reporter

    async def _make_request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
        description: str = "",
        **kwargs
    ) -> Any:
        response = await self.client.request(method, url, json=json, **kwargs)

        # An exchange is evidence, not a verdict — whether a 200 is good or bad
        # depends on the test. Label it by what the server did and let the test
        # outcome carry the pass/fail meaning.
        status = "ALLOWED" if response.is_success else "DENIED"
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

    async def post(self, url: str, json: dict[str, Any] | None = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("POST", url, json=json, description=description, **kwargs)

    async def put(self, url: str, json: dict[str, Any] | None = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PUT", url, json=json, description=description, **kwargs)

    async def delete(self, url: str, description: str = "", **kwargs) -> Any:
        return await self._make_request("DELETE", url, description=description, **kwargs)

    async def patch(self, url: str, json: dict[str, Any] | None = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PATCH", url, json=json, description=description, **kwargs)


@pytest.fixture(scope="session")
def security_reporter():
    """Shared reporter for the entire security test session."""
    reporter = _get_reporter()
    yield reporter
    # Generate the single consolidated report at the end of the session
    report_path = reporter.generate()
    print(f"\nConsolidated security report generated: {report_path}")


@pytest.fixture(autouse=True)
def setup_security_test_section(request, security_reporter):
    """Automatically starts a new section in the reporter for each test."""
    if _is_security_item(request.node):
        security_reporter.start_section(request.node.name, nodeid=request.node.nodeid)
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
async def security_test_data(db_session: AsyncSession) -> dict[str, Any]:
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
        created_at=datetime.now(UTC)
    )
    user_b = UserModel(
        id=str(uuid.uuid4()),
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_b.id,
        password_hash="hashed_secret",
        role_id=user_role.id,
        is_active=True,
        created_at=datetime.now(UTC)
    )
    # Account B also needs an admin so admin-gated surfaces (functions) can be
    # set up symmetrically for both tenants; user_b stays low-privilege on
    # purpose so privilege-escalation tests keep their subject.
    admin_b = UserModel(
        id=str(uuid.uuid4()),
        email=f"admin_b_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_b.id,
        password_hash="hashed_secret",
        role_id=admin_role.id,
        is_active=True,
        created_at=datetime.now(UTC)
    )
    db_session.add_all([user_a, user_b, admin_b])
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
    token_admin_b = jwt_service.create_access_token(
        user_id=admin_b.id,
        account_id=admin_b.account_id,
        email=admin_b.email,
        role="admin"
    )

    return {
        "account_a": account_a,
        "account_b": account_b,
        "user_a": user_a,
        "user_b": user_b,
        "admin_b": admin_b,
        "user_a_token": token_a,
        "user_b_token": token_b,
        "admin_b_token": token_admin_b,
    }


# ---------------------------------------------------------------------------
# Per-surface two-tenant resource fixtures (F1.1)
#
# Every cross-tenant test in later phases needs "a resource owned by A and an
# equivalent resource owned by B" on the surface under attack. These fixtures
# build that pair once per surface, reading account IDs from
# ``security_test_data`` rather than hard-coding them.
# ---------------------------------------------------------------------------


ALPHA_FILE_MARKER = "ALPHA-SECRET-FILE"
BETA_FILE_MARKER = "BETA-SECRET-FILE"


@pytest_asyncio.fixture
async def two_tenant_files(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> AsyncGenerator[dict[str, Any]]:
    """Upload one file per account and yield their storage paths.

    Yields keys: ``account_a_path``, ``account_b_path`` (both ``<account_id>/<uuid>.txt``),
    ``account_a_marker``, ``account_b_marker``, ``storage_root``.
    """
    storage_root = Path(get_settings().storage_path).resolve()
    account_a = security_test_data["account_a"]
    account_b = security_test_data["account_b"]

    async def _upload(token: str, marker: str) -> str:
        response = await client.post(
            "/api/v1/files/upload",
            files={"file": ("secret.txt", BytesIO(marker.encode()), "text/plain")},
            headers=_auth_header(token),
        )
        assert response.status_code == 201, response.text
        return str(response.json()["file"]["path"])

    path_a = await _upload(security_test_data["user_a_token"], ALPHA_FILE_MARKER)
    path_b = await _upload(security_test_data["user_b_token"], BETA_FILE_MARKER)

    yield {
        "account_a_path": path_a,
        "account_b_path": path_b,
        "account_a_marker": ALPHA_FILE_MARKER,
        "account_b_marker": BETA_FILE_MARKER,
        "storage_root": storage_root,
    }

    for account in (account_a, account_b):
        shutil.rmtree(storage_root / account.id, ignore_errors=True)


@pytest_asyncio.fixture
async def two_tenant_collection(
    client: AsyncClient,
    superadmin_token: str,
    security_test_data: dict[str, Any],
) -> dict[str, Any]:
    """Create one shared collection with public rules and one record per account.

    Yields keys: ``collection`` (collection name), ``table`` (``col_<name>``),
    ``account_a_record_id``, ``account_b_record_id``, ``account_a_marker``,
    ``account_b_marker``.
    """
    collection_name = f"vault_{uuid.uuid4().hex[:8]}"
    headers = _auth_header(superadmin_token)

    create_resp = await client.post(
        "/api/v1/collections",
        json={
            "name": collection_name,
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "secret", "type": "text", "required": True},
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text

    # "" means public — the permissive setting the attack tests need so that a
    # denial can only come from account isolation, never from a rule.
    rules_resp = await client.put(
        f"/api/v1/collections/{collection_name}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )
    assert rules_resp.status_code == 200, rules_resp.text

    async def _insert(token: str, marker: str) -> str:
        response = await client.post(
            f"/api/v1/records/{collection_name}",
            json={"title": marker, "secret": marker},
            headers=_auth_header(token),
        )
        assert response.status_code == 201, response.text
        return str(response.json()["id"])

    record_a = await _insert(security_test_data["user_a_token"], "ALPHA-SECRET")
    record_b = await _insert(security_test_data["user_b_token"], "BETA-SECRET")

    return {
        "collection": collection_name,
        "table": f"col_{collection_name}",
        "account_a_record_id": record_a,
        "account_b_record_id": record_b,
        "account_a_marker": "ALPHA-SECRET",
        "account_b_marker": "BETA-SECRET",
    }


@pytest_asyncio.fixture
async def two_tenant_endpoints(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> dict[str, Any]:
    """Create one custom endpoint per account and yield IDs plus dispatcher paths.

    Yields keys: ``account_a_id``/``account_b_id`` (endpoint IDs),
    ``account_a_url``/``account_b_url`` (dispatcher URLs),
    ``account_a_marker``/``account_b_marker``.
    """
    account_a = security_test_data["account_a"]
    account_b = security_test_data["account_b"]

    async def _create(token: str, slug: str, marker: str) -> dict[str, str]:
        path = f"/ping-{uuid.uuid4().hex[:6]}"
        response = await client.post(
            "/api/v1/endpoints",
            json={
                "name": f"probe-{marker.lower()}",
                "path": path,
                "method": "GET",
                "auth_required": True,
                "actions": [],
                "response_template": {"status": 200, "body": {"marker": marker}},
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 201, response.text
        return {"id": str(response.json()["id"]), "url": f"/api/v1/x/{slug}{path}"}

    endpoint_a = await _create(
        security_test_data["user_a_token"], account_a.slug, "ALPHA-ENDPOINT"
    )
    endpoint_b = await _create(
        security_test_data["user_b_token"], account_b.slug, "BETA-ENDPOINT"
    )

    return {
        "account_a_id": endpoint_a["id"],
        "account_b_id": endpoint_b["id"],
        "account_a_url": endpoint_a["url"],
        "account_b_url": endpoint_b["url"],
        "account_a_marker": "ALPHA-ENDPOINT",
        "account_b_marker": "BETA-ENDPOINT",
    }


@pytest_asyncio.fixture
async def two_tenant_functions(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> dict[str, Any]:
    """Create one function per account, skipping cleanly if functions are unavailable.

    Yields keys: ``account_a_slug``/``account_b_slug`` and
    ``account_a_url``/``account_b_url`` (management URLs).
    """

    async def _create(token: str, slug: str) -> str:
        response = await client.post(
            "/api/v1/functions",
            json={"name": slug, "slug": slug, "auth_required": True},
            headers=_auth_header(token),
        )
        if response.status_code in (404, 501, 503):
            pytest.skip(
                f"Functions feature unavailable in this environment "
                f"(POST /api/v1/functions returned {response.status_code})"
            )
        assert response.status_code == 201, response.text
        return str(response.json()["slug"])

    slug_a = await _create(security_test_data["user_a_token"], f"fn-a-{uuid.uuid4().hex[:6]}")
    slug_b = await _create(security_test_data["admin_b_token"], f"fn-b-{uuid.uuid4().hex[:6]}")

    return {
        "account_a_slug": slug_a,
        "account_b_slug": slug_b,
        "account_a_url": f"/api/v1/functions/{slug_a}",
        "account_b_url": f"/api/v1/functions/{slug_b}",
    }
