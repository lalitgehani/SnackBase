
"""Integration tests for invitation acceptance flow."""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import get_db_session, get_current_user, CurrentUser
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    UserModel,
    RoleModel,
    InvitationModel,
)
from sqlalchemy import select
from snackbase.infrastructure.auth import hash_password

@pytest.mark.asyncio
async def test_get_invitation_details(db_session):
    """Test getting invitation details by token."""
    # 1. Setup - Create admin user and account
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TE0003",
        slug=f"test-accept-{uuid.uuid4().hex[:8]}",
        name="Acceptance Test Account",
    )
    db_session.add(account)

    admin_user = UserModel(
        id=str(uuid.uuid4()),
        email=f"admin-accept-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("secure-pass"),
        account_id=account_id,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(admin_user)
    
    # 2. Create an invitation manually
    invitation_token = "valid-token-" + uuid.uuid4().hex
    invitation_id = str(uuid.uuid4())
    invite_email = f"invitee-accept-{uuid.uuid4().hex[:8]}@example.com"
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    
    invitation = InvitationModel(
        id=invitation_id,
        account_id=account_id,
        email=invite_email,
        token=invitation_token,
        invited_by=admin_user.id,
        expires_at=expires_at,
        email_sent=True,
        email_sent_at=datetime.now(timezone.utc)
    )
    db_session.add(invitation)
    await db_session.commit()

    # Override DB session
    app.dependency_overrides[get_db_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # 3. Test Valid Token
        response = await ac.get(f"/api/v1/invitations/{invitation_token}")
        
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["email"] == invite_email
        assert data["account_name"] == account.name
        assert data["is_valid"] is True
        #invited_by_name might be email if name not set
        assert data["invited_by_name"] == admin_user.email 

        # 4. Test Invalid Token
        response = await ac.get("/api/v1/invitations/invalid-token-123")
        assert response.status_code == 404
        assert data["is_valid"] is True # Schema default but verifying valid response structure above

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_invitation_expired(db_session):
    """Test getting expired invitation details."""
    # 1. Setup
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TE0004",
        slug=f"test-expired-{uuid.uuid4().hex[:8]}",
        name="Expired Test Account",
    )
    db_session.add(account)

    admin_user = UserModel(
        id=str(uuid.uuid4()),
        email=f"admin-expired-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("secure-pass"),
        account_id=account_id,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(admin_user)
    
    # 2. Create EXPIRED invitation
    invitation_token = "expired-token-" + uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) - timedelta(hours=1) # Expired 1 hour ago
    
    invitation = InvitationModel(
        id=str(uuid.uuid4()),
        account_id=account_id,
        email=f"expired-{uuid.uuid4().hex[:8]}@example.com",
        token=invitation_token,
        invited_by=admin_user.id,
        expires_at=expires_at,
    )
    db_session.add(invitation)
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Expired Token
        response = await ac.get(f"/api/v1/invitations/{invitation_token}")
        assert response.status_code == 400
        assert response.json()["error"] == "Expired"

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_invitation_already_accepted(db_session):
    """Test getting already accepted invitation details."""
    # 1. Setup
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    account_id = str(uuid.uuid4())
    account = AccountModel(
        id=account_id,
        account_code="TE0005",
        slug=f"test-accepted-{uuid.uuid4().hex[:8]}",
        name="Accepted Test Account",
    )
    db_session.add(account)

    admin_user = UserModel(
        id=str(uuid.uuid4()),
        email=f"admin-accepted-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("secure-pass"),
        account_id=account_id,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(admin_user)
    
    # 2. Create ACCEPTED invitation
    invitation_token = "accepted-token-" + uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    invitation = InvitationModel(
        id=str(uuid.uuid4()),
        account_id=account_id,
        email=f"accepted-{uuid.uuid4().hex[:8]}@example.com",
        token=invitation_token,
        invited_by=admin_user.id,
        expires_at=expires_at,
        accepted_at=datetime.now(timezone.utc) # Accepted just now
    )
    db_session.add(invitation)
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Accepted Token
        response = await ac.get(f"/api/v1/invitations/{invitation_token}")
        assert response.status_code == 400
        assert response.json()["error"] == "Already accepted"

    app.dependency_overrides = {}
