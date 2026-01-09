"""Integration tests for email verification API."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import get_db_session, get_email_service
from snackbase.infrastructure.persistence.models import (
    UserModel,
    EmailVerificationTokenModel,
    RoleModel,
)
from snackbase.infrastructure.auth import jwt_service


@pytest.mark.asyncio
async def test_email_verification_full_flow(db_session):
    """Test the full email verification API flow."""
    # Get user role from seeded roles
    result = await db_session.execute(
        select(RoleModel).where(RoleModel.name == "user")
    )
    user_role = result.scalar_one()

    # 1. Setup - create a user
    import uuid
    user_id = str(uuid.uuid4())
    user = UserModel(
        id=user_id,
        email="verify@example.com",
        password_hash="hashed",
        account_id="00000000-0000-0000-0000-000000000000",
        email_verified=False,
        role_id=user_role.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Mock EmailService to capture the raw token from the call
    mock_email_service = AsyncMock()
    mock_email_service.send_template_email.return_value = True
    # We need to mock _get_system_variables too
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

    # Generate auth token
    auth_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role="user",
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Request verification email
        send_response = await ac.post(
            "/api/v1/auth/send-verification",
            json={"email": "verify@example.com"},
            headers=headers,
        )
        assert send_response.status_code == 200
        assert "Verification email sent" in send_response.json()["message"]

        # Capture the raw token from the mock call
        assert mock_email_service.send_template_email.called
        call_args = mock_email_service.send_template_email.call_args[1]
        raw_token = call_args["variables"]["token"]

        # 3. Verify email with the token
        verify_response = await ac.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_token},
        )
        assert verify_response.status_code == 200
        assert "Email verified successfully" in verify_response.json()["message"]

    # 4. Cleanup and separate verification
    # Re-fetch user from DB
    await db_session.refresh(user)
    assert user.email_verified is True
    assert user.email_verified_at is not None

    # Verify token is marked as used
    result = await db_session.execute(
        select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.user_id == user.id)
    )
    token_model = result.scalar_one()
    assert token_model.used_at is not None

    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_verify_email_invalid_token_integration(db_session):
    """Test verify-email with an invalid token."""
    # Dependency override
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-random-token"},
        )
        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]

    app.dependency_overrides = {}
