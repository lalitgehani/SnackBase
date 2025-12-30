import pytest
from fastapi import status
from tests.security.conftest import AttackClient


@pytest.mark.asyncio
async def test_auth_pw_001_empty_password(attack_client: AttackClient):
    """AUTH-PW-001: Attempt to register with an empty password."""
    payload = {
        "email": "test-empty-pw@example.com",
        "password": "",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with empty password"
    )
    
    # Expected: 400 Bad Request (from validator) or 422 Unprocessable Content (from Pydantic)
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT, 422]
    data = response.json()
    assert "error" in data or "detail" in data
    # Check for specific validation message if possible
    # Based on auth_router.py, it returns a list of details


@pytest.mark.asyncio
async def test_auth_pw_002_short_password(attack_client: AttackClient):
    """AUTH-PW-002: Attempt to register with a password < 12 chars."""
    payload = {
        "email": "test-short-pw@example.com",
        "password": "Short1!",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with too short password (7 chars)"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    codes = [d["code"] for d in data.get("details", [])]
    assert "password_too_short" in codes


@pytest.mark.asyncio
async def test_auth_pw_003_no_uppercase(attack_client: AttackClient):
    """AUTH-PW-003: Attempt to register with no uppercase letter."""
    payload = {
        "email": "test-no-upper@example.com",
        "password": "nouppercase123!",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with no uppercase letter"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    codes = [d["code"] for d in data.get("details", [])]
    assert "password_no_uppercase" in codes


@pytest.mark.asyncio
async def test_auth_pw_004_no_lowercase(attack_client: AttackClient):
    """AUTH-PW-004: Attempt to register with no lowercase letter."""
    payload = {
        "email": "test-no-lower@example.com",
        "password": "NOLOWERCASE123!",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with no lowercase letter"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    codes = [d["code"] for d in data.get("details", [])]
    assert "password_no_lowercase" in codes


@pytest.mark.asyncio
async def test_auth_pw_005_no_digit(attack_client: AttackClient):
    """AUTH-PW-005: Attempt to register with no digits."""
    payload = {
        "email": "test-no-digit@example.com",
        "password": "NoDigitsAllowed!",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with no digits"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    codes = [d["code"] for d in data.get("details", [])]
    assert "password_no_digit" in codes


@pytest.mark.asyncio
async def test_auth_pw_006_no_special(attack_client: AttackClient):
    """AUTH-PW-006: Attempt to register with no special characters."""
    payload = {
        "email": "test-no-special@example.com",
        "password": "NoSpecialChars123",
        "account_name": "Test Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Attempt registration with no special characters"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    codes = [d["code"] for d in data.get("details", [])]
    assert "password_no_special" in codes


@pytest.mark.asyncio
async def test_auth_pw_007_valid_password(attack_client: AttackClient):
    """AUTH-PW-007: Register with a valid password."""
    payload = {
        "email": "valid-pw@example.com",
        "password": "SecurePassword123!",
        "account_name": "Secure Account",
    }
    
    response = await attack_client.post(
        "/api/v1/auth/register",
        json=payload,
        description="Register with a strong password"
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_auth_pw_008_common_passwords(attack_client: AttackClient):
    """AUTH-PW-008: Attempt to register with common passwords (if implemented)."""
    # Currently PasswordValidator does not implement dictionary checks.
    # This test will document the gap.
    common_passwords = ["Password123!", "Admin123!", "Welcome123!"]
    
    for pwd in common_passwords:
        payload = {
            "email": f"common-pw-{pwd}@example.com",
            "password": pwd,
            "account_name": "Common Account",
        }
        
        response = await attack_client.post(
            "/api/v1/auth/register",
            json=payload,
            description=f"Attempt registration with common password: {pwd}"
        )
        
        # If not implemented, this might return 201 (since they meet complexity)
        # We handle this in the security report by marking it as a finding if it passes
        if response.status_code == status.HTTP_201_CREATED:
            attack_client.reporter.log_vulnerability(
                severity="MEDIUM",
                description=f"System allowed common password: {pwd}. Dictionary check not implemented."
            )
