"""Pytest configuration for all tests."""

import asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.persistence.database import Base
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.core.logging import get_logger

logger = get_logger(__name__)



@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    
    return _audit_hooks_registry["registry"]


@pytest_asyncio.fixture
async def db_session(_maybe_enable_audit_hooks) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Uses an in-memory SQLite database for testing.
    """
    # Create in-memory SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Audit hooks are conditionally registered in _init_hooks_conditionally
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


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""
    from snackbase.infrastructure.api.app import app
    from snackbase.infrastructure.persistence.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def superadmin_token(db_session: AsyncSession) -> str:
    """Create a superadmin user and return their access token."""
    # Create valid account
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000000",
        account_code="SY0000",
        name="System Admin",
        slug="system-admin"
    )
    db_session.add(account)
    
    # Get admin role
    admin_role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))).scalar_one()

    # Create superadmin user
    user = UserModel(
        id="superadmin",
        email="superadmin@snackbase.com",
        account_id="00000000-0000-0000-0000-000000000000",
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
