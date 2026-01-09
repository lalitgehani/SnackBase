"""Integration tests for Admin User Verification API."""

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel


@pytest.mark.asyncio
async def test_admin_manual_verification(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test superadmin manually verifying a user."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # 1. Create Account
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="VR0001", name="Verify Test", slug="verify-test")
    db_session.add(account)
    await db_session.commit()

    # 2. Get User Role
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # 3. Create Unverified User
    payload = {
        "email": "unverified@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Verify initial state
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.json()["email_verified"] is False
    assert response.json()["email_verified_at"] is None

    # 4. Manually Verify User
    response = await client.post(f"/api/v1/users/{user_id}/verify", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User email verified successfully"

    # 5. Verify Updated State
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.json()["email_verified"] is True
    assert response.json()["email_verified_at"] is not None

    # 6. Verify Again (Idempotency/Check)
    response = await client.post(f"/api/v1/users/{user_id}/verify", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User email is already verified"


@pytest.mark.asyncio
async def test_admin_resend_verification(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test superadmin resending verification email using a mocked service."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # 1. Setup Data
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="VR0002", name="Resend Test", slug="resend-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    payload = {
        "email": "resend@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # 2. Mock EmailVerificationService.send_verification_email
    with patch("snackbase.domain.services.email_verification_service.EmailVerificationService.send_verification_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # 3. Resend Verification
        response = await client.post(f"/api/v1/users/{user_id}/resend-verification", headers=headers)
        
        assert response.status_code == 200
        assert "Verification email sent" in response.json()["message"]
        
        # Verify mocked service was called correctly
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args["user_id"] == user_id
        assert call_args["email"] == "resend@example.com"
        assert call_args["account_id"] == account_id


@pytest.mark.asyncio
async def test_admin_resend_verification_already_verified(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    """Test resending verification to an already verified user fails."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # 1. Setup Data
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="VR0003", name="Already Test", slug="already-test")
    db_session.add(account)
    await db_session.commit()

    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    payload = {
        "email": "already@example.com",
        "password": "TestPass123!@#",
        "account_id": account_id,
        "role_id": role.id,
    }
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    user_id = response.json()["id"]

    # 2. Manually Verify
    await client.post(f"/api/v1/users/{user_id}/verify", headers=headers)

    # 3. Try to Resend
    response = await client.post(f"/api/v1/users/{user_id}/resend-verification", headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "User email is already verified"


@pytest.mark.asyncio
async def test_access_control(client: AsyncClient, regular_user_token: str):
    """Test regular users cannot access verification endpoints."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    fake_id = str(uuid.uuid4())

    response = await client.post(f"/api/v1/users/{fake_id}/verify", headers=headers)
    assert response.status_code == 403

    response = await client.post(f"/api/v1/users/{fake_id}/resend-verification", headers=headers)
    assert response.status_code == 403
