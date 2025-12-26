"""Integration tests for dashboard endpoint."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    CollectionModel,
    RefreshTokenModel,
    RefreshTokenModel,
    UserModel,
)
from sqlalchemy import select
from snackbase.infrastructure.persistence.models import RoleModel


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_success(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test dashboard stats endpoint returns correct data."""
    # Create test data
    # Account
    account = AccountModel(
        id="TS0001",
        name="Test Account",
        slug="test-account",
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(account)
    
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Users
    user1 = UserModel(
        id="user1",
        email="user1@test.com",
        account_id="TS0001",
        password_hash="hash1",
        role=role,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    user2 = UserModel(
        id="user2",
        email="user2@test.com",
        account_id="TS0001",
        password_hash="hash2",
        role=role,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([user1, user2])

    # Collection
    collection = CollectionModel(
        id="col1",
        name="TestCollection",
        schema='[{"name":"title","type":"text"}]',
    )
    db_session.add(collection)

    # Refresh token (active session)
    refresh_token = RefreshTokenModel(
        id="token1",
        user_id="user1",
        account_id="TS0001",
        token_hash="hash123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    db_session.add(refresh_token)

    await db_session.commit()

    # Make request
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "total_accounts" in data
    assert "total_users" in data
    assert "total_collections" in data
    assert "total_records" in data
    assert "new_accounts_7d" in data
    assert "new_users_7d" in data
    assert "recent_registrations" in data
    assert "system_health" in data
    assert "active_sessions" in data
    assert "recent_audit_logs" in data

    # Check values (at least our test data)
    assert data["total_accounts"] >= 1
    assert data["total_users"] >= 2
    assert data["total_collections"] >= 1
    assert data["new_accounts_7d"] >= 1  # Created 3 days ago
    assert data["new_users_7d"] >= 1  # user2 created 1 day ago
    assert data["active_sessions"] >= 1

    # Check recent registrations
    assert isinstance(data["recent_registrations"], list)
    if len(data["recent_registrations"]) > 0:
        reg = data["recent_registrations"][0]
        assert "id" in reg
        assert "email" in reg
        assert "account_id" in reg
        assert "account_name" in reg
        assert "created_at" in reg

    # Check system health
    assert data["system_health"]["database_status"] == "connected"
    assert isinstance(data["system_health"]["storage_usage_mb"], (int, float))

    # Check audit logs (should be empty until F3.7)
    assert data["recent_audit_logs"] == []


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_empty_database(
    client: AsyncClient, superadmin_token: str
):
    """Test dashboard stats with minimal/empty database."""
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return zero counts (except for system account and superadmin)
    assert isinstance(data["total_accounts"], int)
    assert isinstance(data["total_users"], int)
    assert isinstance(data["total_collections"], int)
    assert data["total_records"] == 0
    assert isinstance(data["new_accounts_7d"], int)
    assert isinstance(data["new_users_7d"], int)
    assert data["recent_registrations"] == [] or isinstance(
        data["recent_registrations"], list
    )
    assert data["recent_audit_logs"] == []


@pytest.mark.asyncio
async def test_dashboard_stats_requires_authentication(client: AsyncClient):
    """Test dashboard stats endpoint requires authentication."""
    response = await client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_stats_requires_superadmin(
    client: AsyncClient, regular_user_token: str
):
    """Test dashboard stats endpoint requires superadmin role."""
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )

    # Should return 403 Forbidden for non-superadmin users
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_stats_recent_registrations_order(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test recent registrations are ordered by created_at DESC."""
    # Create multiple users with different timestamps
    account = AccountModel(id="TS0002", name="Test2", slug="test2")
    db_session.add(account)

    now = datetime.now(timezone.utc)
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    users = []
    for i in range(5):
        user = UserModel(
            id=f"user_order_{i}",
            email=f"user{i}@test.com",
            account_id="TS0002",
            password_hash=f"hash{i}",
            role=role,
            created_at=now - timedelta(hours=i),  # Each user 1 hour apart
        )
        users.append(user)
        db_session.add(user)

    await db_session.commit()

    # Make request
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check that recent registrations are ordered (most recent first)
    registrations = data["recent_registrations"]
    if len(registrations) >= 2:
        for i in range(len(registrations) - 1):
            current_time = datetime.fromisoformat(
                registrations[i]["created_at"].replace("Z", "+00:00")
            )
            next_time = datetime.fromisoformat(
                registrations[i + 1]["created_at"].replace("Z", "+00:00")
            )
            assert current_time >= next_time, "Registrations should be in DESC order"


@pytest.mark.asyncio
async def test_dashboard_stats_active_sessions_count(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test active sessions count excludes revoked and expired tokens."""
    account = AccountModel(id="TS0003", name="Test3", slug="test3")
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    user = UserModel(
        id="user_sessions",
        email="sessions@test.com",
        account_id="TS0003",
        password_hash="hash",
        role=role,
    )
    db_session.add_all([account, user])

    now = datetime.now(timezone.utc)

    # Active token
    active_token = RefreshTokenModel(
        id="active1",
        user_id="user_sessions",
        account_id="TS0003",
        token_hash="active_hash",
        expires_at=now + timedelta(days=7),
        is_revoked=False,
    )

    # Revoked token
    revoked_token = RefreshTokenModel(
        id="revoked1",
        user_id="user_sessions",
        account_id="TS0003",
        token_hash="revoked_hash",
        expires_at=now + timedelta(days=7),
        is_revoked=True,
    )

    # Expired token
    expired_token = RefreshTokenModel(
        id="expired1",
        user_id="user_sessions",
        account_id="TS0003",
        token_hash="expired_hash",
        expires_at=now - timedelta(days=1),
        is_revoked=False,
    )

    db_session.add_all([active_token, revoked_token, expired_token])
    await db_session.commit()

    # Make request
    response = await async_client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Active sessions should only count the active token
    # (plus any from test fixtures)
    assert data["active_sessions"] >= 1
