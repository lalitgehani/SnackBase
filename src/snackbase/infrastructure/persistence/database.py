"""Database abstraction layer using SQLAlchemy 2.0 async.

This module provides the database session management and engine configuration
for SQLAlchemy with async support. It supports both SQLite (aiosqlite) and
PostgreSQL (asyncpg) drivers.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models should inherit from this class to get proper ORM mapping
    and metadata management.
    """

    pass


class DatabaseManager:
    """Database connection and session manager.

    This class manages the async database engine and session factory.
    It provides context managers for database sessions and handles
    connection pooling.
    """

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.settings = get_settings()
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        """Get or create the database engine.

        Returns:
            AsyncEngine: SQLAlchemy async engine instance.
        """
        if self._engine is None:
            self._engine = create_async_engine(
                self.settings.database_url,
                echo=self.settings.db_echo,
                pool_size=self.settings.db_pool_size,
                max_overflow=self.settings.db_max_overflow,
                pool_timeout=self.settings.db_pool_timeout,
                pool_recycle=self.settings.db_pool_recycle,
                # SQLite-specific settings
                connect_args={
                    "check_same_thread": False,
                }
                if self.settings.database_url.startswith("sqlite")
                else {},
            )
            
            # Register systemic audit logging listeners
            # We need the hook registry, but it's not easily available here in DatabaseManager
            # Solution: We can register them in `lifespan` in app.py when we have both app.state.hook_registry and db manager.
            
            logger.info(
                "Database engine created",
                database_url=self._engine.url.render_as_string(hide_password=True),
                pool_size=self.settings.db_pool_size,
            )
        return self._engine

    @property
    def session_factory(self):
        """Get or create the session factory.

        Returns:
            async_sessionmaker: SQLAlchemy async session factory.
        """
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            logger.debug("Database session factory created")
        return self._session_factory

    async def create_tables(self) -> None:
        """Create all database tables.

        This method creates all tables defined in models that inherit
        from Base. Should be called on application startup for development.
        In production, use migrations instead.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data. Only use in testing!
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.warning("Database tables dropped")

    async def disconnect(self) -> None:
        """Close the database engine and all connections.

        Should be called on application shutdown.
        """
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine disposed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope for database operations.

        This context manager creates a new session and ensures it's
        properly closed after use.

        Yields:
            AsyncSession: SQLAlchemy async session.

        Example:
            async with db.session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
        """
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def check_connection(self) -> bool:
        """Check if database connection is working.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.debug("Database connection check successful")
                return True
        except Exception as e:
            logger.error("Database connection check failed", error=str(e))
            return False


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager: Global database manager instance.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session.

    This function is designed to be used as a FastAPI dependency.

    Yields:
        AsyncSession: SQLAlchemy async session.

    Example:
        @app.get("/users")
        async def list_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    db = get_db_manager()
    async with db.session() as session:
        yield session


async def init_database() -> None:
    """Initialize the database.

    This function should be called on application startup.
    It creates tables if they don't exist (development mode).
    In production, migrations should be used instead.
    """
    # Import all models to ensure they are registered with Base.metadata
    # This import must happen before create_tables() is called
    from snackbase.infrastructure.persistence.models import (  # noqa: F401
        AccountModel,
        AuditLogModel,
        CollectionModel,
        GroupModel,
        InvitationModel,
        RoleModel,
        UserModel,
        UsersGroupsModel,
    )

    db = get_db_manager()
    settings = get_settings()

    # Create database directory if using SQLite
    if settings.database_url.startswith("sqlite"):
        # Extract path from sqlite+aiosqlite:///path/to/file.db
        db_path = settings.database_url.split(":///")[-1]
        db_file = Path(db_path)
        db_dir = db_file.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Database directory created", path=str(db_dir))

    # Check connection
    if not await db.check_connection():
        logger.error("Database connection failed")
        raise RuntimeError("Failed to connect to database")

    # Create tables in development (use migrations in production)
    if settings.is_development:
        logger.info("Development mode: Creating database tables")
        await db.create_tables()
        # Seed default roles
        await _seed_default_roles(db, RoleModel)
        # Seed default permissions (after roles are created)
        await _seed_default_permissions(db)
    else:
        logger.info("Production mode: Skipping auto-create, use migrations")

    # Create superadmin from environment variables if configured
    await _create_superadmin_from_env(db)


async def _seed_default_roles(db: DatabaseManager, RoleModel: type) -> None:
    """Seed default roles if they don't exist.

    Args:
        db: Database manager instance.
        RoleModel: The RoleModel class to use for creating roles.
    """
    from sqlalchemy import select

    default_roles = [
        {"id": 1, "name": "admin", "description": "Administrator with full access"},
        {"id": 2, "name": "user", "description": "Regular user with limited access"},
    ]

    async with db.session() as session:
        for role_data in default_roles:
            # Check if role already exists
            result = await session.execute(
                select(RoleModel).where(RoleModel.name == role_data["name"])
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                role = RoleModel(**role_data)
                session.add(role)
                logger.info("Seeded default role", role_name=role_data["name"])

        await session.commit()


async def _seed_default_permissions(db: DatabaseManager) -> None:
    """Seed default permissions if they don't exist.

    Creates default admin permissions with full access to all collections.

    Args:
        db: Database manager instance.
    """
    import json

    from sqlalchemy import select

    from snackbase.infrastructure.persistence.models import PermissionModel, RoleModel

    # Admin role gets full access to all collections (*)
    admin_permission_rules = {
        "create": {"rule": "true", "fields": "*"},
        "read": {"rule": "true", "fields": "*"},
        "update": {"rule": "true", "fields": "*"},
        "delete": {"rule": "true", "fields": "*"},
    }

    async with db.session() as session:
        # Get admin role
        result = await session.execute(
            select(RoleModel).where(RoleModel.name == "admin")
        )
        admin_role = result.scalar_one_or_none()

        if admin_role:
            # Check if permission already exists
            result = await session.execute(
                select(PermissionModel).where(
                    PermissionModel.role_id == admin_role.id,
                    PermissionModel.collection == "*",
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                permission = PermissionModel(
                    role_id=admin_role.id,
                    collection="*",
                    rules=json.dumps(admin_permission_rules),
                )
                session.add(permission)
                logger.info(
                    "Seeded default admin permission",
                    role_id=admin_role.id,
                    collection="*",
                )

        await session.commit()


async def _create_superadmin_from_env(db: DatabaseManager) -> None:
    """Create superadmin from environment variables if configured.

    Checks if SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD are set,
    and creates a superadmin user if one doesn't already exist.

    Args:
        db: Database manager instance.
    """
    from snackbase.core.config import get_settings
    from snackbase.domain.services import (
        SuperadminCreationError,
        SuperadminService,
    )

    settings = get_settings()

    # Only proceed if both email and password are configured
    if not settings.superadmin_email or not settings.superadmin_password:
        logger.debug("Superadmin environment variables not configured, skipping")
        return

    # Check if superadmin already exists
    has_existing = await SuperadminService.has_superadmin(db.session_factory)
    if has_existing:
        logger.info(
            "Superadmin already exists, skipping environment-based creation",
            email=settings.superadmin_email,
        )
        return

    # Create superadmin from environment variables
    try:
        async with db.session() as session:
            user_id, account_id = await SuperadminService.create_superadmin(
                email=settings.superadmin_email,
                password=settings.superadmin_password,
                session=session,
            )

        logger.info(
            "Superadmin created from environment variables",
            user_id=user_id,
            account_id=account_id,
            email=settings.superadmin_email,
        )
    except SuperadminCreationError as e:
        logger.error(
            "Failed to create superadmin from environment variables",
            error=str(e),
            email=settings.superadmin_email,
        )
        # Don't raise - allow application to start


async def close_database() -> None:
    """Close the database connection.

    This function should be called on application shutdown.
    """
    db = get_db_manager()
    await db.disconnect()
