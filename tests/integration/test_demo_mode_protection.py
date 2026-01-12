"""Integration tests for Demo Mode Protection."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.core.config import get_settings

@pytest.fixture
def enable_demo_mode():
    """Fixture to enable demo mode for a test."""
    settings = get_settings()
    original_demo_mode = settings.is_demo
    settings.is_demo = True
    yield
    settings.is_demo = original_demo_mode

@pytest.mark.asyncio
async def test_demo_mode_blocks_superadmin_update(
    client: AsyncClient, 
    superadmin_token: str, 
    db_session: AsyncSession,
    enable_demo_mode
):
    """Test that PATCH /api/v1/users/{id} returns 403 for superadmin in demo mode."""
    # We need a superadmin that is NOT the current logged-in user 
    # (because users_router prevents self-modification anyway)
    
    # Create another superadmin
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))).scalar_one()
    other_superadmin = UserModel(
        id=str(uuid.uuid4()),
        account_id=SYSTEM_ACCOUNT_ID,
        email="other_admin@example.com",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    db_session.add(other_superadmin)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {superadmin_token}"}
    payload = {"email": "new_admin_email@example.com"}
    
    response = await client.patch(f"/api/v1/users/{other_superadmin.id}", json=payload, headers=headers)
    
    assert response.status_code == 403
    assert "Demo mode" in response.json()["detail"]

@pytest.mark.asyncio
async def test_demo_mode_blocks_superadmin_password_reset(
    client: AsyncClient, 
    superadmin_token: str, 
    db_session: AsyncSession,
    enable_demo_mode
):
    """Test that PUT /api/v1/users/{id}/password returns 403 for superadmin in demo mode."""
    # Create another superadmin
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))).scalar_one()
    other_superadmin = UserModel(
        id=str(uuid.uuid4()),
        account_id=SYSTEM_ACCOUNT_ID,
        email="other_admin_pw@example.com",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    db_session.add(other_superadmin)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {superadmin_token}"}
    payload = {"new_password": "NewStrongPass123!@#"}
    
    response = await client.put(f"/api/v1/users/{other_superadmin.id}/password", json=payload, headers=headers)
    
    assert response.status_code == 403
    assert "Demo mode" in response.json()["detail"]

@pytest.mark.asyncio
async def test_demo_mode_blocks_superadmin_deactivation(
    client: AsyncClient, 
    superadmin_token: str, 
    db_session: AsyncSession,
    enable_demo_mode
):
    """Test that DELETE /api/v1/users/{id} returns 403 for superadmin in demo mode."""
    # Create another superadmin
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))).scalar_one()
    other_superadmin = UserModel(
        id=str(uuid.uuid4()),
        account_id=SYSTEM_ACCOUNT_ID,
        email="other_admin_del@example.com",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    db_session.add(other_superadmin)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    response = await client.delete(f"/api/v1/users/{other_superadmin.id}", headers=headers)
    
    assert response.status_code == 403
    assert "Demo mode" in response.json()["detail"]

@pytest.mark.asyncio
async def test_demo_mode_allows_regular_user_modification(
    client: AsyncClient, 
    superadmin_token: str, 
    db_session: AsyncSession,
    enable_demo_mode
):
    """Test that regular users can still be modified in demo mode."""
    # Create a regular account and user
    account_id = str(uuid.uuid4())
    account = AccountModel(id=account_id, account_code="RA1234", name="Regular Account", slug="regular-account")
    db_session.add(account)
    
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    regular_user = UserModel(
        id=str(uuid.uuid4()),
        account_id=account_id,
        email="regular@example.com",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    db_session.add(regular_user)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    # 1. Test update
    response = await client.patch(
        f"/api/v1/users/{regular_user.id}", 
        json={"email": "updated_regular@example.com"}, 
        headers=headers
    )
    assert response.status_code == 200
    
    # 2. Test password reset
    response = await client.put(
        f"/api/v1/users/{regular_user.id}/password", 
        json={"new_password": "AnotherStrongPass123!@#"}, 
        headers=headers
    )
    assert response.status_code == 200
    
    # 3. Test deactivation
    response = await client.delete(f"/api/v1/users/{regular_user.id}", headers=headers)
    assert response.status_code == 204
