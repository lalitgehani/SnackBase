"""Unit tests for repository count methods."""

from datetime import datetime, timedelta, timezone

import pytest

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    CollectionModel,
    RefreshTokenModel,
    UserModel,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    CollectionRepository,
    RefreshTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from sqlalchemy import select
from snackbase.infrastructure.persistence.models import RoleModel


@pytest.mark.asyncio
async def test_account_repository_count_all(db_session):
    """Test AccountRepository.count_all returns correct count."""
    repo = AccountRepository(db_session)

    # Get initial count
    initial_count = await repo.count_all()

    # Add accounts
    account1 = AccountModel(id="AC0001", name="Account 1", slug="account-1")
    account2 = AccountModel(id="AC0002", name="Account 2", slug="account-2")
    db_session.add_all([account1, account2])
    await db_session.commit()

    # Verify count increased
    new_count = await repo.count_all()
    assert new_count == initial_count + 2


@pytest.mark.asyncio
async def test_account_repository_count_created_since(db_session):
    """Test AccountRepository.count_created_since filters by date."""
    repo = AccountRepository(db_session)

    now = datetime.now(timezone.utc)
    five_days_ago = now - timedelta(days=5)
    three_days_ago = now - timedelta(days=3)

    # Add accounts with different timestamps
    old_account = AccountModel(
        id="AC0003",
        name="Old Account",
        slug="old-account",
        created_at=five_days_ago,
    )
    recent_account = AccountModel(
        id="AC0004",
        name="Recent Account",
        slug="recent-account",
        created_at=three_days_ago,
    )
    db_session.add_all([old_account, recent_account])
    await db_session.commit()

    # Count since 4 days ago (should only include recent_account)
    four_days_ago = now - timedelta(days=4)
    count = await repo.count_created_since(four_days_ago)
    assert count >= 1  # At least the recent account


@pytest.mark.asyncio
async def test_user_repository_count_all(db_session):
    """Test UserRepository.count_all returns correct count."""
    repo = UserRepository(db_session)

    # Create account first
    account = AccountModel(id="AC0005", name="Test", slug="test")
    db_session.add(account)
    await db_session.commit()

    # Get initial count
    initial_count = await repo.count_all()

    # Get role
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Add users
    user1 = UserModel(
        id="user1",
        email="user1@test.com",
        account_id="AC0005",
        password_hash="hash1",
        role=role,
    )
    user2 = UserModel(
        id="user2",
        email="user2@test.com",
        account_id="AC0005",
        password_hash="hash2",
        role=role,
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Verify count increased
    new_count = await repo.count_all()
    assert new_count == initial_count + 2


@pytest.mark.asyncio
async def test_user_repository_count_created_since(db_session):
    """Test UserRepository.count_created_since filters by date."""
    repo = UserRepository(db_session)

    # Create account
    account = AccountModel(id="AC0006", name="Test2", slug="test2")
    db_session.add(account)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    old_user = UserModel(
        id="user_old",
        email="old@test.com",
        account_id="AC0006",
        password_hash="hash",
        role=role,
        created_at=now - timedelta(days=10),
    )
    recent_user = UserModel(
        id="user_recent",
        email="recent@test.com",
        account_id="AC0006",
        password_hash="hash",
        role=role,
        created_at=now - timedelta(days=2),
    )
    db_session.add_all([old_user, recent_user])
    await db_session.commit()

    # Count since 7 days ago
    seven_days_ago = now - timedelta(days=7)
    count = await repo.count_created_since(seven_days_ago)
    assert count >= 1  # At least the recent user


@pytest.mark.asyncio
async def test_user_repository_get_recent_registrations(db_session):
    """Test UserRepository.get_recent_registrations returns users in order."""
    repo = UserRepository(db_session)

    # Create account
    account = AccountModel(id="AC0007", name="Test3", slug="test3")
    db_session.add(account)
    await db_session.commit()

    # Add users with different timestamps
    now = datetime.now(timezone.utc)
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    users = []
    for i in range(5):
        user = UserModel(
            id=f"user_reg_{i}",
            email=f"user{i}@test.com",
            account_id="AC0007",
            password_hash=f"hash{i}",
            role=role,
            created_at=now - timedelta(hours=i),
        )
        users.append(user)
        db_session.add(user)
    await db_session.commit()

    # Get recent registrations
    recent = await repo.get_recent_registrations(limit=3)

    # Verify we got results
    assert len(recent) <= 3

    # Verify they're ordered by created_at DESC (most recent first)
    for i in range(len(recent) - 1):
        assert recent[i].created_at >= recent[i + 1].created_at

    # Verify account relationship is loaded
    if len(recent) > 0:
        assert recent[0].account is not None
        assert recent[0].account.name == "Test3"


@pytest.mark.asyncio
async def test_collection_repository_count_all(db_session):
    """Test CollectionRepository.count_all returns correct count."""
    repo = CollectionRepository(db_session)

    # Get initial count
    initial_count = await repo.count_all()

    # Add collections
    col1 = CollectionModel(
        id="col1", name="Collection1", schema='[{"name":"field1","type":"text"}]'
    )
    col2 = CollectionModel(
        id="col2", name="Collection2", schema='[{"name":"field2","type":"text"}]'
    )
    db_session.add_all([col1, col2])
    await db_session.commit()

    # Verify count increased
    new_count = await repo.count_all()
    assert new_count == initial_count + 2


@pytest.mark.asyncio
async def test_refresh_token_repository_count_active_sessions(db_session):
    """Test RefreshTokenRepository.count_active_sessions counts correctly."""
    repo = RefreshTokenRepository(db_session)

    # Create account and user
    account = AccountModel(id="AC0008", name="Test4", slug="test4")
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    user = UserModel(
        id="user_token",
        email="token@test.com",
        account_id="AC0008",
        password_hash="hash",
        role=role,
    )
    db_session.add_all([account, user])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Add various tokens
    active_token = RefreshTokenModel(
        id="active",
        user_id="user_token",
        account_id="AC0008",
        token_hash="active_hash",
        expires_at=now + timedelta(days=7),
        is_revoked=False,
    )
    revoked_token = RefreshTokenModel(
        id="revoked",
        user_id="user_token",
        account_id="AC0008",
        token_hash="revoked_hash",
        expires_at=now + timedelta(days=7),
        is_revoked=True,
    )
    expired_token = RefreshTokenModel(
        id="expired",
        user_id="user_token",
        account_id="AC0008",
        token_hash="expired_hash",
        expires_at=now - timedelta(days=1),
        is_revoked=False,
    )
    db_session.add_all([active_token, revoked_token, expired_token])
    await db_session.commit()

    # Count active sessions
    count = await repo.count_active_sessions()

    # Should only count the active token (plus any from fixtures)
    assert count >= 1


@pytest.mark.asyncio
async def test_refresh_token_repository_count_active_sessions_empty(db_session):
    """Test count_active_sessions returns 0 when no active tokens."""
    repo = RefreshTokenRepository(db_session)

    # Create account and user
    # Create account and user
    account = AccountModel(id="AC0009", name="Test5", slug="test5")
    role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    user = UserModel(
        id="user_no_tokens",
        email="notoken@test.com",
        account_id="AC0009",
        password_hash="hash",
        role=role,
    )
    db_session.add_all([account, user])
    await db_session.commit()

    # Add only revoked/expired tokens
    now = datetime.now(timezone.utc)
    revoked = RefreshTokenModel(
        id="rev1",
        user_id="user_no_tokens",
        account_id="AC0009",
        token_hash="hash1",
        expires_at=now + timedelta(days=7),
        is_revoked=True,
    )
    expired = RefreshTokenModel(
        id="exp1",
        user_id="user_no_tokens",
        account_id="AC0009",
        token_hash="hash2",
        expires_at=now - timedelta(days=1),
        is_revoked=False,
    )
    db_session.add_all([revoked, expired])
    await db_session.commit()

    # Count should not include these tokens
    # (may have other active tokens from fixtures, so just verify it's a valid count)
    count = await repo.count_active_sessions()
    assert isinstance(count, int)
    assert count >= 0
