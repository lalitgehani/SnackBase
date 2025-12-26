"""Unit tests for AccountRepository."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.persistence.repositories import AccountRepository


@pytest.mark.asyncio
async def test_create_account(db_session):
    """Test creating an account."""
    repo = AccountRepository(db_session)
    account = AccountModel(
        id="AA0001",
        name="Test Account",
        slug="test-account",
        created_at=datetime.now(timezone.utc),
    )

    created = await repo.create(account)
    assert created.id == "AA0001"
    assert created.name == "Test Account"

    # Verify persistence
    fetched = await repo.get_by_id("AA0001")
    assert fetched is not None
    assert fetched.name == "Test Account"


@pytest.mark.asyncio
async def test_get_all_paginated_default(db_session):
    """Verify pagination works."""
    repo = AccountRepository(db_session)
    
    # Create 30 accounts
    for i in range(30):
        account = AccountModel(
            id=f"AA{i:04d}",
            name=f"Account {i}",
            slug=f"account-{i}",
            created_at=datetime.now(timezone.utc) + timedelta(minutes=i),
        )
        db_session.add(account)
    await db_session.commit()

    # Page 1 (Descending sort by default, so last inserted comes first)
    accounts, total = await repo.get_all_paginated(page=1, page_size=10)
    assert len(accounts) == 10
    assert total == 30
    assert accounts[0].id == "AA0029"  # Newest first
    
    # Page 2
    accounts_p2, total_p2 = await repo.get_all_paginated(page=2, page_size=10)
    assert len(accounts_p2) == 10
    
    # Page 4 (empty)
    accounts_p4, total_p4 = await repo.get_all_paginated(page=4, page_size=10)
    assert len(accounts_p4) == 0


@pytest.mark.asyncio
async def test_get_all_paginated_with_search(db_session):
    """Verify search by name, slug, ID."""
    repo = AccountRepository(db_session)
    
    accounts = [
        AccountModel(id="AA0001", name="Alpha Corp", slug="alpha-corp"),
        AccountModel(id="BB0002", name="Beta Inc", slug="beta-inc"),
        AccountModel(id="CC0003", name="Gamma Ltd", slug="gamma-ltd"),
    ]
    for acc in accounts:
        db_session.add(acc)
    await db_session.commit()

    # Search by name
    results, total = await repo.get_all_paginated(search_query="Alpha")
    assert total == 1
    assert results[0].name == "Alpha Corp"

    # Search by slug
    results, total = await repo.get_all_paginated(search_query="beta-inc")
    assert total == 1
    assert results[0].slug == "beta-inc"

    # Search by ID
    results, total = await repo.get_all_paginated(search_query="CC0003")
    assert total == 1
    assert results[0].id == "CC0003"


@pytest.mark.asyncio
async def test_get_all_paginated_with_sort(db_session):
    """Verify sorting by each column."""
    repo = AccountRepository(db_session)
    
    # Add accounts with different attributes
    now = datetime.now(timezone.utc)
    accounts = [
        AccountModel(id="AA0001", name="C Name", slug="c-slug", created_at=now),
        AccountModel(id="BB0002", name="A Name", slug="a-slug", created_at=now + timedelta(hours=1)),
        AccountModel(id="CC0003", name="B Name", slug="b-slug", created_at=now + timedelta(hours=2)),
    ]
    for acc in accounts:
        db_session.add(acc)
    await db_session.commit()

    # Sort by Name ASC
    results, _ = await repo.get_all_paginated(sort_by="name", sort_order="asc")
    assert [a.name for a in results] == ["A Name", "B Name", "C Name"]

    # Sort by Created At DESC
    results, _ = await repo.get_all_paginated(sort_by="created_at", sort_order="desc")
    assert [a.id for a in results] == ["CC0003", "BB0002", "AA0001"]


@pytest.mark.asyncio
async def test_update_account(db_session):
    """Verify account update."""
    repo = AccountRepository(db_session)
    account = AccountModel(id="AA0001", name="Old Name", slug="old-slug")
    await repo.create(account)

    account.name = "New Name"
    updated = await repo.update(account)
    
    assert updated.name == "New Name"
    
    # Verify in DB
    refreshed = await repo.get_by_id("AA0001")
    assert refreshed.name == "New Name"


@pytest.mark.asyncio
async def test_delete_account(db_session):
    """Verify account deletion."""
    repo = AccountRepository(db_session)
    account = AccountModel(id="AA0001", name="To Delete", slug="to-delete")
    await repo.create(account)

    await repo.delete(account)
    
    found = await repo.get_by_id("AA0001")
    assert found is None


@pytest.mark.asyncio
async def test_get_user_count(db_session):
    """Verify user count calculation."""
    repo = AccountRepository(db_session)
    account = AccountModel(id="AA0001", name="Account 1", slug="acc-1")
    await repo.create(account)
    
    # Add role required for user
    role = RoleModel(name="user", description="User")
    db_session.add(role)
    await db_session.flush()

    # Add users
    for i in range(5):
        user = UserModel(
            id=f"user{i}",
            email=f"user{i}@example.com",
            account_id="AA0001",
            role=role,  # Assign role
            password_hash="hash"
        )
        db_session.add(user)
    await db_session.commit()

    count = await repo.get_user_count("AA0001")
    assert count == 5
    
    count_empty = await repo.get_user_count("NONEXISTENT")
    assert count_empty == 0


@pytest.mark.asyncio
async def test_get_with_stats(db_session):
    """Verify account with stats (count methods)."""
    repo = AccountRepository(db_session)
    
    # Add accounts
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=2)
    new = now
    
    db_session.add(AccountModel(id="AA0001", name="Old", slug="old", created_at=old))
    db_session.add(AccountModel(id="BB0002", name="New", slug="new", created_at=new))
    await db_session.commit()

    assert await repo.count_all() == 2
    
    # Count created since yesterday
    since_yesterday = await repo.count_created_since(now - timedelta(days=1))
    assert since_yesterday == 1  # Only "New" account
