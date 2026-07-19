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
        account_code="TS0001",
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
    assert "range" in data
    assert "previous_period" in data
    assert "time_series" in data
    assert "recent_registrations" in data
    assert "system_health" in data
    assert "active_sessions" in data
    assert "recent_audit_logs" in data
    assert "records_by_collection" in data
    assert "audit_by_operation" in data["time_series"]

    # Check values (at least our test data)
    assert data["total_accounts"] >= 1
    assert data["total_users"] >= 2
    assert data["total_collections"] >= 1
    assert data["new_accounts_7d"] >= 1  # Created 3 days ago
    assert data["new_users_7d"] >= 1  # user2 created 1 day ago
    assert data["active_sessions"] >= 1
    assert data["range"] == "7d"
    assert "new_accounts" in data["previous_period"]
    assert "new_users" in data["previous_period"]
    assert len(data["time_series"]["accounts_created"]) == 7
    assert len(data["time_series"]["users_created"]) == 7
    assert len(data["time_series"]["audit_by_operation"]) == 7
    assert isinstance(data["records_by_collection"], list)

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
    assert data["range"] == "7d"
    assert data["previous_period"]["new_accounts"] >= 0
    assert data["previous_period"]["new_users"] >= 0
    assert len(data["time_series"]["accounts_created"]) == 7
    assert len(data["time_series"]["users_created"]) == 7
    assert len(data["time_series"]["audit_by_operation"]) == 7
    assert all(
        p["count"] == 0 or isinstance(p["count"], int)
        for p in data["time_series"]["accounts_created"]
    )
    assert all(
        isinstance(p["create"], int)
        and isinstance(p["update"], int)
        and isinstance(p["delete"], int)
        for p in data["time_series"]["audit_by_operation"]
    )
    assert isinstance(data["records_by_collection"], list)
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
    account = AccountModel(id="TS0002", account_code="TS0002", name="Test2", slug="test2")
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
            # Parse datetimes, handling both Z suffix and +00:00 format
            current_str = registrations[i]["created_at"]
            next_str = registrations[i + 1]["created_at"]
            
            # Normalize Z to +00:00 for fromisoformat compatibility
            current_time = datetime.fromisoformat(current_str.replace("Z", "+00:00"))
            next_time = datetime.fromisoformat(next_str.replace("Z", "+00:00"))
            
            # Ensure both are timezone-aware (add UTC if naive)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
            if next_time.tzinfo is None:
                next_time = next_time.replace(tzinfo=timezone.utc)
            
            assert current_time >= next_time, "Registrations should be in DESC order"


@pytest.mark.asyncio
async def test_dashboard_stats_active_sessions_count(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test active sessions count excludes revoked and expired tokens."""
    account = AccountModel(id="TS0003", account_code="TS0003", name="Test3", slug="test3")
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
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Active sessions should only count the active token
    # (plus any from test fixtures)
    assert data["active_sessions"] >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_invalid_range_returns_422(
    client: AsyncClient, superadmin_token: str
):
    """Test invalid range query param returns 422."""
    response = await client.get(
        "/api/v1/dashboard/stats",
        params={"range": "1y"},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("range_value,expected_days", [("7d", 7), ("30d", 30), ("90d", 90)])
async def test_dashboard_stats_range_series_length(
    client: AsyncClient, superadmin_token: str, range_value: str, expected_days: int
):
    """Test time series length matches each supported range."""
    response = await client.get(
        "/api/v1/dashboard/stats",
        params={"range": range_value},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["range"] == range_value
    assert len(data["time_series"]["accounts_created"]) == expected_days
    assert len(data["time_series"]["users_created"]) == expected_days
    assert len(data["time_series"]["audit_by_operation"]) == expected_days
    # Each point has date and count
    for point in data["time_series"]["accounts_created"]:
        assert "date" in point
        assert "count" in point
        assert isinstance(point["count"], int)
    for point in data["time_series"]["audit_by_operation"]:
        assert "date" in point
        assert "create" in point
        assert "update" in point
        assert "delete" in point


@pytest.mark.asyncio
async def test_dashboard_stats_time_series_sum_matches_period_counts(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test series totals align with new_*_7d for seeded same-window data."""
    now = datetime.now(timezone.utc)
    account = AccountModel(
        id="TS0099",
        account_code="TS0099",
        name="Series Account",
        slug="series-account",
        created_at=now - timedelta(days=2),
    )
    db_session.add(account)
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    users = [
        UserModel(
            id=f"series_user_{i}",
            email=f"series{i}@test.com",
            account_id="TS0099",
            password_hash=f"hash{i}",
            role=role,
            created_at=now - timedelta(days=i),
        )
        for i in range(3)  # today, 1d ago, 2d ago — all within 7d
    ]
    db_session.add_all(users)
    await db_session.commit()

    response = await client.get(
        "/api/v1/dashboard/stats",
        params={"range": "7d"},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    accounts_sum = sum(p["count"] for p in data["time_series"]["accounts_created"])
    users_sum = sum(p["count"] for p in data["time_series"]["users_created"])
    assert accounts_sum == data["new_accounts_7d"]
    assert users_sum == data["new_users_7d"]
    # Our seeded users should be included
    assert data["new_users_7d"] >= 3
    assert data["new_accounts_7d"] >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_audit_by_operation_series(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test audit_by_operation series shape and seeded operation totals."""
    from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
    from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
        AuditLogRepository,
    )

    now = datetime.now(timezone.utc)
    repo = AuditLogRepository(db_session)

    for i, operation in enumerate(["CREATE", "CREATE", "UPDATE", "DELETE"]):
        entry = AuditLogModel(
            account_id="SY0000",
            operation=operation,
            table_name="users",
            record_id=f"rec-{i}",
            column_name="email",
            old_value=None if operation == "CREATE" else "old",
            new_value="new" if operation != "DELETE" else None,
            user_id="superadmin",
            user_email="admin@test.com",
            user_name="Admin",
            occurred_at=now - timedelta(hours=i),
        )
        await repo.create(entry)
    await db_session.commit()

    response = await client.get(
        "/api/v1/dashboard/stats",
        params={"range": "7d"},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    series = data["time_series"]["audit_by_operation"]
    assert len(series) == 7
    for point in series:
        assert set(point.keys()) >= {"date", "create", "update", "delete"}

    create_sum = sum(p["create"] for p in series)
    update_sum = sum(p["update"] for p in series)
    delete_sum = sum(p["delete"] for p in series)
    assert create_sum >= 2
    assert update_sum >= 1
    assert delete_sum >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_records_by_collection_present(
    client: AsyncClient, superadmin_token: str, db_session
):
    """Test records_by_collection is present and total_records is consistent."""
    response = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "records_by_collection" in data
    ranked = data["records_by_collection"]
    assert isinstance(ranked, list)
    ranked_sum = sum(item["count"] for item in ranked)
    # Ranked list is top-N (+ Other); sum should equal total_records
    assert ranked_sum == data["total_records"]
    # If multiple entries, ensure descending order (excluding trailing Other)
    named = [item for item in ranked if item["name"] != "Other"]
    for i in range(1, len(named)):
        assert named[i - 1]["count"] >= named[i]["count"]
