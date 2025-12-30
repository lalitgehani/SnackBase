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


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
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
        
    # Register global listeners for tests
    # We need the hook registry from the app
    from snackbase.infrastructure.api.app import app
    from snackbase.infrastructure.persistence.event_listeners import register_sqlalchemy_listeners
    
    # Ensure app hooks are initialized (lifespan might not have run yet)
    if not hasattr(app.state, "hook_registry"):
        # Manually init if needed, or rely on create_app having run it (it does in module scope)
        # app = create_app() -> initializes hooks
        pass
        
    if hasattr(app.state, "hook_registry"):
        register_sqlalchemy_listeners(engine, app.state.hook_registry)

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
