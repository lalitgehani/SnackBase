import pytest
import pytest_asyncio
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.auth import hash_password, jwt_service
from tests.security.conftest import AttackClient


@pytest_asyncio.fixture
async def token_test_user(db_session: AsyncSession):
    """Create a test user for token management testing."""
    # Get user role
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result.scalar_one()

    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="TK0001",
        name="Token Test Account",
        slug="token-test"
    )
    db_session.add(account)

    password = "SecurePassword123!"
    user = UserModel(
        id=str(uuid.uuid4()),
        email="test-token@example.com",
        account_id=account.id,
        password_hash=hash_password(password),
        role_id=user_role.id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    
    return {
        "user_id": user.id,
        "email": user.email,
        "password": password,
        "account_code": account.account_code,
        "account_id": account.id,
        "role": user_role.name
    }


@pytest.mark.asyncio
async def test_auth_tk_001_expired_access_token(attack_client: AttackClient, token_test_user):
    """AUTH-TK-001: Attempt access with an expired access token."""
    # Create an expired token manually
    payload = {
        "iss": jwt_service.ISSUER,
        "sub": token_test_user["user_id"],
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "user_id": token_test_user["user_id"],
        "account_id": token_test_user["account_id"],
        "email": token_test_user["email"],
        "role": token_test_user["role"],
        "type": "access",
    }
    expired_token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    
    # Try to access a protected endpoint
    response = await attack_client.get(
        "/api/v1/auth/me",
        headers=headers,
        description="Access with expired access token"
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_auth_tk_002_malformed_jwt(attack_client: AttackClient):
    """AUTH-TK-002: Attempt access with a malformed JWT."""
    malformed_tokens = [
        "not-a-jwt",
        "header.payload.signature-extra",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.invalid",
    ]
    
    for token in malformed_tokens:
        headers = {"Authorization": f"Bearer {token}"}
        response = await attack_client.get(
            "/api/v1/auth/me",
            headers=headers,
            description=f"Access with malformed JWT: {token}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_tk_003_tampered_token_signature(attack_client: AttackClient, token_test_user):
    """AUTH-TK-003: Attempt access with a tampered token signature."""
    # 1. Create a valid token
    valid_token = jwt_service.create_access_token(
        user_id=token_test_user["user_id"],
        account_id=token_test_user["account_id"],
        email=token_test_user["email"],
        role=token_test_user["role"]
    )
    
    # 2. Tamper with the payload (e.g., change account_id)
    header, payload_b64, signature = valid_token.split(".")
    import base64
    import json
    
    # Decode payload
    padding = "=" * (4 - len(payload_b64) % 4)
    payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode()
    payload = json.loads(payload_json)
    
    # Change something
    payload["account_id"] = "SY0000"
    
    # Encode back
    tampered_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    tampered_token = f"{header}.{tampered_payload_b64}.{signature}"
    
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = await attack_client.get(
        "/api/v1/auth/me",
        headers=headers,
        description="Access with tampered token signature"
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_tk_004_valid_refresh_token(attack_client: AttackClient, token_test_user):
    """AUTH-TK-004: Successfully refresh tokens with a valid refresh token."""
    # 1. Login to get tokens
    login_payload = {
        "email": token_test_user["email"],
        "password": token_test_user["password"],
        "account": token_test_user["account_code"]
    }
    login_response = await attack_client.post("/api/v1/auth/login", json=login_payload, description="Initial login")
    assert login_response.status_code == status.HTTP_200_OK
    refresh_token = login_response.json()["refresh_token"]
    
    # 2. Refresh tokens
    refresh_payload = {"refresh_token": refresh_token}
    response = await attack_client.post("/api/v1/auth/refresh", json=refresh_payload, description="Valid token refresh")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_auth_tk_005_expired_refresh_token(attack_client: AttackClient, token_test_user):
    """AUTH-TK-005: Attempt refresh with an expired refresh token."""
    # Create an expired refresh token manually
    payload = {
        "iss": jwt_service.ISSUER,
        "sub": token_test_user["user_id"],
        "iat": datetime.now(timezone.utc) - timedelta(days=2),
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
        "jti": str(uuid.uuid4()),
        "user_id": token_test_user["user_id"],
        "account_id": token_test_user["account_id"],
        "type": "refresh",
    }
    expired_token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
    
    refresh_payload = {"refresh_token": expired_token}
    response = await attack_client.post("/api/v1/auth/refresh", json=refresh_payload, description="Expired refresh token")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_tk_006_used_refresh_token_replay(attack_client: AttackClient, token_test_user):
    """AUTH-TK-006: Attempt to reuse a refresh token that has already been rotated."""
    # 1. Login
    login_payload = {
        "email": token_test_user["email"],
        "password": token_test_user["password"],
        "account": token_test_user["account_code"]
    }
    login_response = await attack_client.post("/api/v1/auth/login", json=login_payload, description="Initial login")
    refresh_token = login_response.json()["refresh_token"]
    
    # 2. Use it once
    refresh_payload = {"refresh_token": refresh_token}
    await attack_client.post("/api/v1/auth/refresh", json=refresh_payload, description="First refresh (rotation)")
    
    # 3. Use it again (replay)
    response = await attack_client.post("/api/v1/auth/refresh", json=refresh_payload, description="Replay refresh token")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_tk_007_refresh_token_rotation(attack_client: AttackClient, token_test_user):
    """AUTH-TK-007: Verify refresh token rotation (old one invalidated)."""
    # This is essentially AUTH-TK-006 but focuses on the rotation logic
    # 1. Login
    login_payload = {
        "email": token_test_user["email"],
        "password": token_test_user["password"],
        "account": token_test_user["account_code"]
    }
    login_response = await attack_client.post("/api/v1/auth/login", json=login_payload, description="Initial login")
    old_refresh_token = login_response.json()["refresh_token"]
    
    # 2. Refresh
    response = await attack_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}, description="Rotate refresh token")
    new_refresh_token = response.json()["refresh_token"]
    
    assert new_refresh_token != old_refresh_token
    
    # 3. Verify old is invalid
    response = await attack_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}, description="Verify old token is invalid")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # 4. Verify new is valid
    response = await attack_client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token}, description="Verify new token is valid")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_auth_tk_008_token_without_account_id(attack_client: AttackClient, token_test_user):
    """AUTH-TK-008: Attempt access with a token missing account_id claim."""
    payload = {
        "iss": jwt_service.ISSUER,
        "sub": token_test_user["user_id"],
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "user_id": token_test_user["user_id"],
        # "account_id": missing,
        "email": token_test_user["email"],
        "role": token_test_user["role"],
        "type": "access",
    }
    invalid_token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
    
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = await attack_client.get(
        "/api/v1/auth/me",
        headers=headers,
        description="Access with token missing account_id"
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
