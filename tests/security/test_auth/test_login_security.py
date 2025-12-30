import pytest
import pytest_asyncio
import uuid
import time
import statistics
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.auth import hash_password
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
