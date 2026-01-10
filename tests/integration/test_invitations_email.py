
"""Integration tests for invitation system email functionality."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import get_db_session, get_email_service, get_current_user, CurrentUser
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    UserModel,
    RoleModel,
    InvitationModel,
)
from sqlalchemy import select
from snackbase.infrastructure.auth import hash_password

@pytest.fixture
async def mock_email_service():
    service = AsyncMock()
    service.send_template_email.return_value = True
    return service

@pytest.mark.asyncio
async def test_invitation_email_flow(db_session, mock_email_service):
    """Test the full invitation email flow."""
    # 1. Setup - Create admin user
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TE0001",
        slug=f"test-invitation-{uuid.uuid4().hex[:8]}",
        name="Invitation Test Account",
    )
    db_session.add(account)

    admin_user_id = str(uuid.uuid4())
    admin_user = UserModel(
        id=admin_user_id,
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("secure-pass"),
        account_id=account_id,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    # 2. Override dependencies
    async def override_get_db_session():
        yield db_session

    async def override_get_email_service():
        return mock_email_service

    async def override_get_current_user():
        return CurrentUser(
            user_id=admin_user.id,
            account_id=account.id,
            email=admin_user.email,
            role="admin",
            groups=[],
        )

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_email_service] = override_get_email_service
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # 3. Create Invitation
        invite_email = f"invitee-{uuid.uuid4().hex[:8]}@example.com"
        response = await ac.post(
            "/api/v1/invitations",
            json={"email": invite_email}
        )
        
        # 4. Verify Response
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["email"] == invite_email
        assert data["email_sent"] is True
        assert data["email_sent_at"] is not None
        
        # 5. Verify Email Service Call
        assert mock_email_service.send_template_email.called
        call_args = mock_email_service.send_template_email.call_args
        kwargs = call_args.kwargs
        
        assert kwargs["to"] == invite_email
        assert kwargs["template_type"] == "invitation"
        assert kwargs["account_id"] == account_id
        
        variables = kwargs["variables"]
        assert variables["email"] == invite_email
        assert variables["account_name"] == account.name
        assert "invitation_url" in variables
        assert "token" in variables
        
        # 6. Verify Log in DB (via email_sent flag update)
        # Note: We mocked the service, so actual email log isn't in DB,
        # but the invitation update happens in the router after successful send.
        
        stmt = select(InvitationModel).where(InvitationModel.id == data["id"])
        result = await db_session.execute(stmt)
        invitation = result.scalar_one()
        
        assert invitation.email_sent is True
        assert invitation.email_sent_at is not None

    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_invitation_email_failure_handling(db_session):
    """Test that invitation is created even if email sending fails."""
    # 1. Setup (similar to above, simplify by reusing if possible, but keeping separate)
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TE0002",
        slug=f"test-fail-{uuid.uuid4().hex[:8]}",
        name="Fail Test Account",
    )
    db_session.add(account)

    admin_user = UserModel(
        id=str(uuid.uuid4()),
        email=f"admin-fail-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("secure-pass"),
        account_id=account_id,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    # 2. Mock failing email service
    mock_failing_service = AsyncMock()
    mock_failing_service.send_template_email.side_effect = Exception("SMTP Error")

    # Override
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_email_service] = lambda: mock_failing_service
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=admin_user.id,
        account_id=account.id,
        email=admin_user.email,
        role="admin",
        groups=[]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # 3. Create Invitation
        invite_email = f"fail-invite-{uuid.uuid4().hex[:8]}@example.com"
        response = await ac.post(
            "/api/v1/invitations",
            json={"email": invite_email}
        )
        
        # 4. Verify Success Response (but email_sent=False)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["email"] == invite_email
        assert data["email_sent"] is False # Should be False
        # assert data["email_sent_at"] is None # Might be None or not present? Model defaults to None. Schema defaults to None.
        
        # 5. Verify DB State
        stmt = select(InvitationModel).where(InvitationModel.id == data["id"])
        result = await db_session.execute(stmt)
        invitation = result.scalar_one()
        
        assert invitation.email_sent is False
        assert invitation.email_sent_at is None

    app.dependency_overrides = {}
