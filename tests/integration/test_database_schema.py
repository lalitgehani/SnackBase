"""Integration tests for F1.2 Database Schema & Core System Tables."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    UserModel,
    RoleModel,
    GroupModel,
    CollectionModel,
    InvitationModel,
    UsersGroupsModel,
)


@pytest.mark.asyncio
async def test_database_tables_exist(db_session: AsyncSession):
    """Test that all core system tables exist in the database."""
    # We need to get the sync engine/connection to use inspect
    # db_session.bind is the AsyncEngine
    
    def get_table_names(conn):
        inspector = inspect(conn)
        return inspector.get_table_names()

    async with db_session.bind.connect() as conn:
        table_names = await conn.run_sync(get_table_names)
    
    expected_tables = {
        "accounts",
        "users",
        "roles",
        "groups",
        "users_groups",
        "collections",
        "invitations",
    }
    
    for table in expected_tables:
        assert table in table_names, f"Table {table} not found in database"


@pytest.mark.asyncio
async def test_accounts_table_schema(db_session: AsyncSession):
    """Test accounts table schema."""
    def get_columns(conn):
        inspector = inspect(conn)
        return {col["name"]: col for col in inspector.get_columns("accounts")}

    async with db_session.bind.connect() as conn:
        columns = await conn.run_sync(get_columns)
    
    assert "id" in columns
    assert "slug" in columns
    assert "name" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    
    # Check types/nullability if needed, but existence is the first step
    assert not columns["id"]["nullable"]
    assert not columns["slug"]["nullable"]
    assert not columns["name"]["nullable"]


@pytest.mark.asyncio
async def test_users_table_schema(db_session: AsyncSession):
    """Test users table schema and foreign keys."""
    def inspect_table(conn):
        inspector = inspect(conn)
        return {
            "columns": {col["name"]: col for col in inspector.get_columns("users")},
            "fks": inspector.get_foreign_keys("users"),
        }

    async with db_session.bind.connect() as conn:
        info = await conn.run_sync(inspect_table)
    
    columns = info["columns"]
    fks = info["fks"]
    
    # Check columns
    expected_columns = [
        "id", "account_id", "email", "password_hash", 
        "role_id", "created_at", "updated_at", 
        "last_login", "is_active"
    ]
    for col in expected_columns:
        assert col in columns
    
    # Check foreign keys
    # fks is a list of dicts: {'name': ..., 'constrained_columns': ['account_id'], 'referred_schema': None, 'referred_table': 'accounts', 'referred_columns': ['id']}
    
    account_fk = next((fk for fk in fks if fk["referred_table"] == "accounts"), None)
    assert account_fk is not None
    assert "account_id" in account_fk["constrained_columns"]
    
    role_fk = next((fk for fk in fks if fk["referred_table"] == "roles"), None)
    assert role_fk is not None
    assert "role_id" in role_fk["constrained_columns"]


@pytest.mark.asyncio
async def test_roles_model_operations(db_session: AsyncSession):
    """Test that we can insert and query roles (verifying model functionality)."""
    # Insert a role
    new_role = RoleModel(name="test_role", description="Test Role")
    db_session.add(new_role)
    await db_session.commit()
    
    # Query it back
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "test_role"))
    role = result.scalar_one()
    
    assert role.name == "test_role"
    assert role.description == "Test Role"
    assert role.id is not None


@pytest.mark.asyncio
async def test_account_creation(db_session: AsyncSession):
    """Test creating an account with validation."""
    account = AccountModel(
        id="XX1234",
        slug="test-account",
        name="Test Account"
    )
    db_session.add(account)
    await db_session.commit()
    
    result = await db_session.execute(select(AccountModel).where(AccountModel.slug == "test-account"))
    retrieved = result.scalar_one()
    
    assert retrieved.id == "XX1234"
    assert retrieved.name == "Test Account"


@pytest.mark.asyncio
async def test_group_relationships(db_session: AsyncSession):
    """Test group relationships with users."""
    # Setup account and role needed for user/group
    account = AccountModel(id="XY5678", slug="group-test", name="Group Test")
    role = RoleModel(name="group_user", description="Group User")
    db_session.add_all([account, role])
    await db_session.commit()
    
    # Create group
    import uuid
    group = GroupModel(id=str(uuid.uuid4()), account_id=account.id, name="Test Group", description="Desc")
    db_session.add(group)
    await db_session.commit()
    
    # Create user
    user = UserModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        email="user@test.com",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    # Add user to group - use direct model to avoid async lazy load issues
    user_group = UsersGroupsModel(user_id=user.id, group_id=group.id)
    db_session.add(user_group)
    await db_session.commit()
    
    # Verify association exists
    result = await db_session.execute(
        select(UsersGroupsModel).where(
            UsersGroupsModel.user_id == user.id,
            UsersGroupsModel.group_id == group.id
        )
    )
    assert result.scalar_one() is not None

