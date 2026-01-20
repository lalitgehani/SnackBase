"""Pytest configuration for all tests."""

import os
import asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.persistence.database import Base
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.core.logging import get_logger

logger = get_logger(__name__)



@pytest.fixture(autouse=True)
def _setup_config_registry():
    """Ensure config_registry is initialized on app state for tests."""
    from snackbase.infrastructure.api.app import app
    from snackbase.core.configuration.config_registry import ConfigurationRegistry
    from snackbase.infrastructure.security.encryption import EncryptionService
    
    if not hasattr(app.state, "config_registry"):
        # Use a consistent test key
        encryption_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
        app.state.config_registry = ConfigurationRegistry(encryption_service)
    
    # Clear registry memory state for isolation between tests
    app.state.config_registry._provider_definitions = {}
    app.state.config_registry._cache = {}
    
    yield app.state.config_registry


@pytest.fixture(autouse=True)
def _clean_dynamic_migrations():
    """Clear the dynamic migrations directory before running tests."""
    import shutil
    import os
    
    dynamic_dir = os.path.abspath("sb_data/migrations")
    if os.path.exists(dynamic_dir):
        # Keep the .gitkeep if it exists, or just clear everything
        for filename in os.listdir(dynamic_dir):
            if filename == ".gitkeep":
                continue
            file_path = os.path.join(dynamic_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(dynamic_dir, exist_ok=True)
    
    yield


@pytest.fixture(scope="session")
def _audit_hooks_registry():
    """Provide access to the hook registry and track registration status.
    
    Returns a dict with 'registry' and 'registered' keys.
    This prevents duplicate registrations across test sessions.
    """
    from snackbase.infrastructure.api.app import app
    
    registry = app.state.hook_registry if hasattr(app.state, "hook_registry") else None
    return {"registry": registry, "registered": False}


@pytest.fixture
def _maybe_enable_audit_hooks(request, _audit_hooks_registry):
    """Conditionally enable audit hooks based on test markers.
    
    By default, NO hooks are registered (matching original behavior for fast tests).
    Only tests marked with @pytest.mark.enable_audit_hooks will have audit logging.
    
    IMPORTANT: The original conftest.py did NOT register builtin_hooks at all,
    which is why tests were fast. We restore that behavior here.
    """
    # Check if this test wants audit hooks enabled
    enable_audit = request.node.get_closest_marker("enable_audit_hooks") is not None
    
    if enable_audit and not _audit_hooks_registry["registered"]:
        # First test requesting audit hooks - register them globally
        registry = _audit_hooks_registry["registry"]
        if registry:
            from snackbase.infrastructure.hooks import register_builtin_hooks
            from snackbase.infrastructure.persistence.event_listeners import register_sqlalchemy_listeners
            
            # Register built-in hooks (includes audit logging hooks)
            register_builtin_hooks(registry)
            
            # Register SQLAlchemy listeners (global Mapper class listeners)
            register_sqlalchemy_listeners(None, registry)
            
            _audit_hooks_registry["registered"] = True
            logger.info("Audit hooks enabled for tests")
    
    # Register cleanup after all tests
    @request.addfinalizer
    def cleanup_listeners():
        if _audit_hooks_registry["registered"]:
            from snackbase.infrastructure.persistence.event_listeners import (
                unregister_sqlalchemy_listeners,
            )

            unregister_sqlalchemy_listeners()
            _audit_hooks_registry["registered"] = False
            logger.info("Audit hooks unregistered after test")

    return _audit_hooks_registry["registry"]


@pytest.fixture
def with_audit_disabled(monkeypatch):
    """Fixture to test with audit logging disabled."""
    from snackbase.core.config import get_settings
    # Set env var BEFORE clearing cache
    monkeypatch.setenv("SNACKBASE_AUDIT_LOGGING_ENABLED", "false")
    # Clear cache so next call picks up new env var
    get_settings.cache_clear()
    yield
    # Cleanup: restore default settings
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session(_maybe_enable_audit_hooks) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Uses a unique local SQLite database for each test runner process
    to prevent interference between parallel test runs.
    """
    db_file = f"test_db_{os.getpid()}.sqlite"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Enable WAL mode and set busy timeout for better concurrency
    async with engine.connect() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.commit()

    # Apply all migrations to set up the schema
    from snackbase.infrastructure.persistence.migration_service import MigrationService
    migration_service = MigrationService(engine=engine)
    await migration_service.apply_migrations()
        
    # Audit hooks are conditionally registered
    # based on the @pytest.mark.enable_audit_hooks marker

    # Create session
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Seed default roles
    from snackbase.infrastructure.persistence.models.role import RoleModel
    async with async_session_maker() as session:
        admin_role = RoleModel(name="admin", description="Administrator")
        user_role = RoleModel(name="user", description="Standard User")
        session.add_all([admin_role, user_role])
        await session.commit()

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""
    from snackbase.infrastructure.api.app import app
    from snackbase.infrastructure.persistence.database import get_db_session

    async def _get_db_session_override():
        yield db_session

    app.dependency_overrides[get_db_session] = _get_db_session_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def superadmin_token(db_session: AsyncSession) -> str:
    """Create a superadmin user and return their access token."""
    # Get or create system account (SY0000)
    # The migration creates this account, but we handle the case where it doesn't exist
    result = await db_session.execute(
        select(AccountModel).where(AccountModel.account_code == "SY0000")
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        # Create system account if it doesn't exist (e.g., if migration hasn't run)
        account = AccountModel(
            id="00000000-0000-0000-0000-000000000000",
            account_code="SY0000",
            name="System Account",
            slug="system"
        )
        db_session.add(account)
        await db_session.flush()
    
    # Get admin role
    admin_role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))).scalar_one()

    # Create superadmin user
    user = UserModel(
        id="superadmin",
        email="superadmin@snackbase.com",
        account_id=account.id,
        password_hash="hashed_secret",
        role=admin_role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()

    # Generate token
    token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role="admin",
    )
    return token


@pytest_asyncio.fixture
async def regular_user_token(db_session: AsyncSession) -> str:
    """Create a regular user and return their access token."""
    # Create valid account
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000001",
        account_code="RU0000",
        name="Regular User Account",
        slug="reg-user-acc"
    )
    db_session.add(account)

    # Get user role
    user_role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()

    # Create regular user
    user = UserModel(
        id="regular_user",
        email="user@snackbase.com",
        account_id="00000000-0000-0000-0000-000000000001",
        password_hash="hashed_secret",
        role=user_role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()

    # Generate token
    token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role="user",
    )
    return token
