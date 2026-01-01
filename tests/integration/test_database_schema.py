"""Integration tests for F1.2 Database Schema & Core System Tables."""

import uuid

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    CollectionModel,
    GroupModel,
    InvitationModel,
    RoleModel,
    UserModel,
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
        "audit_log",
        "users",
        "roles",
        "groups",
        "users_groups",
        "collections",
        "invitations",
        "configurations",
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
        account_code="XX1234",
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
    account = AccountModel(
        id="XY5678", account_code="XY5678", slug="group-test", name="Group Test"
    )
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


@pytest.mark.asyncio
async def test_configurations_table_exists(db_session: AsyncSession):
    """Test that configurations table exists in the database."""

    def get_table_names(conn):
        inspector = inspect(conn)
        return inspector.get_table_names()

    async with db_session.bind.connect() as conn:
        table_names = await conn.run_sync(get_table_names)

    assert "configurations" in table_names, "Table configurations not found in database"


@pytest.mark.asyncio
async def test_configurations_table_schema(db_session: AsyncSession):
    """Test configurations table schema has all required columns."""

    def get_columns(conn):
        inspector = inspect(conn)
        return {col["name"]: col for col in inspector.get_columns("configurations")}

    async with db_session.bind.connect() as conn:
        columns = await conn.run_sync(get_columns)

    # Check all required columns exist
    required_columns = [
        "id",
        "account_id",
        "category",
        "provider_name",
        "display_name",
        "logo_url",
        "config_schema",
        "config",
        "enabled",
        "is_builtin",
        "is_system",
        "priority",
        "created_at",
        "updated_at",
    ]
    for col in required_columns:
        assert col in columns, f"Column {col} not found in configurations table"

    # Check nullability
    assert not columns["id"]["nullable"]
    assert not columns["account_id"]["nullable"]
    assert not columns["category"]["nullable"]
    assert not columns["provider_name"]["nullable"]
    assert not columns["display_name"]["nullable"]
    assert columns["logo_url"]["nullable"]
    assert columns["config_schema"]["nullable"]
    assert not columns["config"]["nullable"]
    assert not columns["enabled"]["nullable"]
    assert not columns["is_builtin"]["nullable"]
    assert not columns["is_system"]["nullable"]
    assert not columns["priority"]["nullable"]


@pytest.mark.asyncio
async def test_configurations_unique_constraint(db_session: AsyncSession):
    """Test unique constraint on (category, provider_name, account_id)."""
    from snackbase.infrastructure.persistence.models import ConfigurationModel

    # Create test account
    account = AccountModel(
        id="CF1234", account_code="CF1234", slug="config-test", name="Config Test"
    )
    db_session.add(account)
    await db_session.commit()

    # Create first configuration
    config1 = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="auth_providers",
        provider_name="google",
        display_name="Google OAuth",
        config={"client_id": "test"},
    )
    db_session.add(config1)
    await db_session.commit()

    # Try to create duplicate configuration (same category, provider, account)
    config2 = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="auth_providers",
        provider_name="google",
        display_name="Google OAuth 2",
        config={"client_id": "test2"},
    )
    db_session.add(config2)

    # Should raise IntegrityError due to unique constraint
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_configurations_cascade_delete(db_session: AsyncSession):
    """Test that configurations are deleted when account is deleted (CASCADE)."""
    from snackbase.infrastructure.persistence.models import ConfigurationModel

    # Create test account
    account = AccountModel(
        id="CD1234", account_code="CD1234", slug="cascade-test", name="Cascade Test"
    )
    db_session.add(account)
    await db_session.commit()

    # Create configuration for this account
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="email_providers",
        provider_name="ses",
        display_name="Amazon SES",
        config={"region": "us-east-1"},
    )
    db_session.add(config)
    await db_session.commit()

    config_id = config.id

    # Delete the account
    await db_session.delete(account)
    await db_session.commit()

    # Verify configuration was also deleted
    result = await db_session.execute(
        select(ConfigurationModel).where(ConfigurationModel.id == config_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_configurations_indexes(db_session: AsyncSession):
    """Test that required indexes exist on configurations table."""

    def get_indexes(conn):
        inspector = inspect(conn)
        return {idx["name"]: idx for idx in inspector.get_indexes("configurations")}

    async with db_session.bind.connect() as conn:
        indexes = await conn.run_sync(get_indexes)

    # Check required indexes exist
    expected_indexes = [
        "ix_configurations_category_account",
        "ix_configurations_category_provider",
        "ix_configurations_is_system",
    ]
    for idx_name in expected_indexes:
        assert idx_name in indexes, f"Index {idx_name} not found on configurations table"


@pytest.mark.asyncio
async def test_system_account_exists(db_session: AsyncSession):
    """Test that system account (SY0000) exists."""
    result = await db_session.execute(
        select(AccountModel).where(AccountModel.account_code == "SY0000")
    )
    system_account = result.scalar_one_or_none()

    assert system_account is not None, "System account (SY0000) not found"
    assert system_account.account_code == "SY0000"
    assert system_account.slug == "system"
    assert system_account.id == "00000000-0000-0000-0000-000000000000"
