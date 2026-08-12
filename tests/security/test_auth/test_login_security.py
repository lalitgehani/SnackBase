import statistics
import time
import uuid

import pytest
import pytest_asyncio
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth import hash_password
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from tests.security.conftest import AttackClient


@pytest_asyncio.fixture
async def login_test_user(db_session: AsyncSession):
    """Create a test user with a known password for login testing."""
    # Get user role
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result.scalar_one()

    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="AT0001",
        name="Auth Test Account",
        slug="auth-test"
    )
    db_session.add(account)

    password = "SecurePassword123!"
    user = UserModel(
        id=str(uuid.uuid4()),
        email="test-login@example.com",
        account_id=account.id,
        password_hash=hash_password(password),
        role_id=user_role.id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "email": user.email,
        "password": password,
        "account": account.account_code,
        "account_slug": account.slug,
        "account_id": account.id
    }


@pytest.mark.asyncio
async def test_auth_li_001_non_existent_email(attack_client: AttackClient, login_test_user):
    """AUTH-LI-001: Attempt login with non-existent email."""
    payload = {
        "email": "non-existent@example.com",
        "password": login_test_user["password"],
        "account": login_test_user["account"],
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with non-existent email"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"] == "Authentication failed"
    assert data["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_auth_li_002_wrong_password(attack_client: AttackClient, login_test_user):
    """AUTH-LI-002: Attempt login with wrong password."""
    payload = {
        "email": login_test_user["email"],
        "password": "WrongPassword123!",
        "account": login_test_user["account"],
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with wrong password"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"] == "Authentication failed"
    assert data["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_auth_li_003_wrong_account(attack_client: AttackClient, login_test_user):
    """AUTH-LI-003: Attempt login with wrong account identifier."""
    payload = {
        "email": login_test_user["email"],
        "password": login_test_user["password"],
        "account": "WR0001",
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with wrong account"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"] == "Authentication failed"
    assert data["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_auth_li_004_valid_credentials(attack_client: AttackClient, login_test_user):
    """AUTH-LI-004: Login with valid credentials."""
    payload = {
        "email": login_test_user["email"],
        "password": login_test_user["password"],
        "account": login_test_user["account"],
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with valid credentials"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == login_test_user["email"]


@pytest.mark.asyncio
async def test_auth_li_005_missing_account(attack_client: AttackClient):
    """AUTH-LI-005: Attempt login with missing account field."""
    payload = {
        "email": "test@example.com",
        "password": "Password123!",
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with missing account"
    )

    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT, 422]


@pytest.mark.asyncio
async def test_auth_li_006_missing_email(attack_client: AttackClient):
    """AUTH-LI-006: Attempt login with missing email field."""
    payload = {
        "account": "AC1234",
        "password": "Password123!",
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with missing email"
    )

    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT, 422]


@pytest.mark.asyncio
async def test_auth_li_007_missing_password(attack_client: AttackClient):
    """AUTH-LI-007: Attempt login with missing password field."""
    payload = {
        "account": "AC1234",
        "email": "test@example.com",
    }

    response = await attack_client.post(
        "/api/v1/auth/login",
        json=payload,
        description="Login with missing password"
    )

    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT, 422]


@pytest.mark.asyncio
async def test_auth_li_008_timing_attack_prevention(attack_client: AttackClient, login_test_user):
    """AUTH-LI-008: Verify timing attack prevention for login.

    The response time for a valid email vs invalid email should be similar
    because the system should perform a dummy password verification.
    """
    valid_payload = {
        "email": login_test_user["email"],
        "password": "WrongPassword1!",
        "account": login_test_user["account"],
    }

    invalid_payload = {
        "email": "definitely-not-exists@example.com",
        "password": "WrongPassword1!",
        "account": login_test_user["account"],
    }

    valid_times = []
    invalid_times = []
    iterations = 5  # Small number for CI, but enough to see if there's a huge gap

    # Warm up
    await attack_client.post("/api/v1/auth/login", json=invalid_payload)

    for _ in range(iterations):
        start = time.perf_counter()
        await attack_client.post("/api/v1/auth/login", json=valid_payload)
        valid_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        await attack_client.post("/api/v1/auth/login", json=invalid_payload)
        invalid_times.append(time.perf_counter() - start)

    avg_valid = statistics.mean(valid_times)
    avg_invalid = statistics.mean(invalid_times)
    diff = abs(avg_valid - avg_invalid)

    print(f"Avg Valid: {avg_valid:.4f}s, Avg Invalid: {avg_invalid:.4f}s, Diff: {diff:.4f}s")

    # Threshold of 100ms is generous for Argon2 which takes ~500ms+ by default
    # But SQLite in-memory might be very fast.
    if diff > 0.1:
        attack_client.reporter.log_vulnerability(
            severity="MEDIUM",
            description=f"Potential timing attack: Difference between valid/invalid email login is {diff:.4f}s"
        )

    assert diff < 0.2, f"Timing difference too high: {diff:.4f}s"


# ---------------------------------------------------------------------------
# AUTH-LI-* enumeration uniformity (M-07)
#
# When an account uses OAuth or SAML, `/auth/login` answers a password attempt
# with 400 and a body naming `auth_provider`, `provider_name` and a redirect
# URL — before any credential has been proven. An unknown address gets a
# generic 401. The two are trivially distinguishable, so the endpoint is an
# oracle for "does this address exist here, and which IdP does it use". The
# second half is the more useful answer: it tells an attacker exactly which
# identity provider to phish.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sso_only_user(db_session: AsyncSession):
    """A user in the same account whose auth_provider is SAML, not password."""
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()

    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="SS0001",
        name="SSO Test Account",
        slug=f"sso-test-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(account)

    user = UserModel(
        id=str(uuid.uuid4()),
        email=f"sso-{uuid.uuid4().hex[:6]}@example.com",
        account_id=account.id,
        password_hash=hash_password("IrrelevantPassword1!"),
        role_id=user_role.id,
        is_active=True,
        email_verified=True,
        auth_provider="saml",
        auth_provider_name="okta",
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "email": user.email,
        "account": account.account_code,
    }


@pytest.mark.asyncio
async def test_auth_li_010_sso_only_user_returns_generic_401(
    attack_client: AttackClient, sso_only_user
):
    """AUTH-LI-010: an SSO-only user must answer like an unknown address."""
    response = await attack_client.post(
        "/api/v1/auth/login",
        json={
            "email": sso_only_user["email"],
            "password": "WrongPassword1!",
            "account": sso_only_user["account"],
        },
        description="Password login attempt against an SSO-only user",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        f"SSO-only users are distinguishable from unknown users: {response.text}"
    )


@pytest.mark.asyncio
async def test_auth_li_011_sso_response_discloses_no_provider_details(
    attack_client: AttackClient, sso_only_user
):
    """AUTH-LI-011: no provider name or redirect may leak pre-authentication."""
    response = await attack_client.post(
        "/api/v1/auth/login",
        json={
            "email": sso_only_user["email"],
            "password": "WrongPassword1!",
            "account": sso_only_user["account"],
        },
        description="Checking for provider disclosure before credential proof",
    )

    body = response.text
    for marker in ("auth_provider", "provider_name", "redirect_url", "okta"):
        assert marker not in body, (
            f"login disclosed {marker!r} before any credential was proven"
        )


@pytest.mark.asyncio
async def test_auth_li_012_sso_and_unknown_user_are_indistinguishable(
    attack_client: AttackClient, sso_only_user
):
    """AUTH-LI-012: the two responses must match in status and body shape."""
    sso_response = await attack_client.post(
        "/api/v1/auth/login",
        json={
            "email": sso_only_user["email"],
            "password": "WrongPassword1!",
            "account": sso_only_user["account"],
        },
        description="SSO-only user login attempt",
    )
    unknown_response = await attack_client.post(
        "/api/v1/auth/login",
        json={
            "email": f"nobody-{uuid.uuid4().hex[:6]}@example.com",
            "password": "WrongPassword1!",
            "account": sso_only_user["account"],
        },
        description="Unknown user login attempt",
    )

    assert sso_response.status_code == unknown_response.status_code
    assert sorted(sso_response.json().keys()) == sorted(unknown_response.json().keys())
