"""Integration tests for password reset API."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from unittest.mock import AsyncMock

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import get_db_session, get_email_service
from snackbase.infrastructure.persistence.models import (
    UserModel,
    AccountModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    RoleModel,
)
from snackbase.infrastructure.auth import hash_password, jwt_service


@pytest.mark.asyncio
async def test_password_reset_full_flow(db_session):
    """Test the full password reset API flow."""
    # Get user role from seeded roles
    result = await db_session.execute(
        select(RoleModel).where(RoleModel.name == "user")
    )
    user_role = result.scalar_one()

    # 1. Setup - create an account and user
    import uuid
    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TS0001",
        slug="test-reset",
        name="Test Reset Account",
    )
    db_session.add(account)

    user_id = str(uuid.uuid4())
    original_password = "old-password-123"
    user = UserModel(
        id=user_id,
        email="reset@example.com",
        password_hash=hash_password(original_password),
        account_id=account_id,
        email_verified=True,
        role_id=user_role.id,
        auth_provider="password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(account)

    # Mock EmailService to capture the raw token
    mock_email_service = AsyncMock()
    mock_email_service.send_template_email.return_value = True
    mock_email_service._get_system_variables = AsyncMock(
        return_value={"app_url": "http://localhost:3000"}
    )

    # Dependency overrides
    async def override_get_db_session():
        yield db_session

    async def override_get_email_service():
        return mock_email_service

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_email_service] = override_get_email_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Request password reset
        forgot_response = await ac.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset@example.com", "account": "test-reset"},
        )
        assert forgot_response.status_code == 200
        assert "password reset link has been sent" in forgot_response.json()["message"]

        # Capture the raw token from the mock call
        assert mock_email_service.send_template_email.called
        call_args = mock_email_service.send_template_email.call_args[1]
        raw_token = call_args["variables"]["token"]

        # 3. Verify token is valid
        verify_response = await ac.get(
            f"/api/v1/auth/verify-reset-token/{raw_token}",
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True
        assert verify_response.json()["expires_at"] is not None

        # 4. Reset password with the token
        new_password = "NewSecure123!"
        reset_response = await ac.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": new_password},
        )
        assert reset_response.status_code == 200
        assert "Password reset successfully" in reset_response.json()["message"]

    # 5. Verify password was changed
    await db_session.refresh(user)
    from snackbase.infrastructure.auth import verify_password
    assert verify_password(new_password, user.password_hash)
    assert not verify_password(original_password, user.password_hash)

    # 6. Verify token is marked as used
    result = await db_session.execute(
        select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    )
    token_model = result.scalar_one()
    assert token_model.used_at is not None

    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_user(db_session):
    """Test forgot password with non-existent user (should still return 200)."""
    # Dependency override
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com", "account": "nonexistent"},
        )
        # Should return 200 for security (don't reveal user existence)
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_reset_password_invalid_token(db_session):
    """Test reset password with invalid token."""
    # Dependency override
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid-token", "new_password": "NewPassword123!"},
        )
        assert response.status_code == 400
        assert "Invalid, expired, or already used reset token" in response.json()["detail"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_reset_password_weak_password(db_session):
    """Test reset password with weak password."""
    # Dependency override
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token", "new_password": "weak"},
        )
        assert response.status_code == 422  # Pydantic validation error
        assert "at least 8 characters" in str(response.json())

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_reset_password_invalidates_refresh_tokens(db_session):
    """Test that password reset invalidates all refresh tokens."""
    # Get user role from seeded roles
    result = await db_session.execute(
        select(RoleModel).where(RoleModel.name == "user")
    )
    user_role = result.scalar_one()

    # 1. Setup - create account, user, and refresh tokens
    import uuid
    from datetime import datetime, timedelta, timezone

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TS0002",
        slug="test-refresh",
        name="Test Refresh Account",
    )
    db_session.add(account)

    user_id = str(uuid.uuid4())
    user = UserModel(
        id=user_id,
        email="refresh@example.com",
        password_hash=hash_password("old-password"),
        account_id=account_id,
        email_verified=True,
        role_id=user_role.id,
        auth_provider="password",
    )
    db_session.add(user)

    # Create some refresh tokens
    token1 = RefreshTokenModel(
        id=str(uuid.uuid4()),
        token_hash="hash1",
        user_id=user_id,
        account_id=account_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    token2 = RefreshTokenModel(
        id=str(uuid.uuid4()),
        token_hash="hash2",
        user_id=user_id,
        account_id=account_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    db_session.add(token1)
    db_session.add(token2)
    await db_session.commit()

    # Mock EmailService
    mock_email_service = AsyncMock()
    mock_email_service.send_template_email.return_value = True
    mock_email_service._get_system_variables = AsyncMock(
        return_value={"app_url": "http://localhost:3000"}
    )

    # Dependency overrides
    async def override_get_db_session():
        yield db_session

    async def override_get_email_service():
        return mock_email_service

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_email_service] = override_get_email_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Request password reset
        await ac.post(
            "/api/v1/auth/forgot-password",
            json={"email": "refresh@example.com", "account": "test-refresh"},
        )

        # Get token
        call_args = mock_email_service.send_template_email.call_args[1]
        raw_token = call_args["variables"]["token"]

        # 3. Reset password
        await ac.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword123!"},
        )

    # 4. Verify all refresh tokens are revoked
    await db_session.refresh(token1)
    await db_session.refresh(token2)
    assert token1.is_revoked is True
    assert token2.is_revoked is True

    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_verify_reset_token_invalid(db_session):
    """Test verify reset token with invalid token."""
    # Dependency override
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/auth/verify-reset-token/invalid-token")
        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert response.json()["expires_at"] is None

    app.dependency_overrides = {}
