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
from sqlalchemy import event

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

            # Apply SQLite pragmas on connection
            if self.settings.database_url.startswith("sqlite"):
                @event.listens_for(self._engine.sync_engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute(f"PRAGMA journal_mode={self.settings.db_sqlite_journal_mode}")
                    cursor.execute(f"PRAGMA synchronous={self.settings.db_sqlite_synchronous}")
                    cursor.execute(f"PRAGMA cache_size={self.settings.db_sqlite_cache_size}")
                    cursor.execute(f"PRAGMA temp_store={self.settings.db_sqlite_temp_store}")
                    cursor.execute(f"PRAGMA mmap_size={self.settings.db_sqlite_mmap_size}")
                    cursor.execute(f"PRAGMA busy_timeout={self.settings.db_sqlite_busy_timeout}")
                    
                    fk_status = "ON" if self.settings.db_sqlite_foreign_keys else "OFF"
                    cursor.execute(f"PRAGMA foreign_keys={fk_status}")
                    
                    cursor.close()
                    logger.debug("Applied SQLite performance pragmas and configured foreign keys")

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

    # Run Alembic migrations to ensure database is up to date
    # This works for both development and production
    logger.info("Running Alembic migrations to initialize/update database")
    try:
        import asyncio
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config("alembic.ini")
        # Ensure we use the correct database URL
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        # Run migrations to head in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
        
        # Seed default roles and permissions after migrations
        await _seed_default_roles(db, RoleModel)
        await _seed_default_permissions(db)
    except Exception as e:
        logger.error("Failed to run Alembic migrations", error=str(e))
        raise RuntimeError(f"Database initialization failed: {e}")

    # Create superadmin from environment variables if configured
    await _create_superadmin_from_env(db)
    
    # Seed default configurations
    await _seed_default_configurations(db)
    
    # Seed default email templates
    await _seed_default_email_templates(db)


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
    async with db.session() as session:
        has_existing = await SuperadminService.has_superadmin(session)
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
        # Don't raise - allow application to start


async def _seed_default_configurations(db: DatabaseManager) -> None:
    """Seed default configurations if they don't exist.

    Args:
        db: Database manager instance.
    """
    import uuid
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
    from snackbase.infrastructure.configuration.providers.auth.email_password import EmailPasswordProvider
    
    # SYSTEM_ACCOUNT_ID constant
    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
    
    ep_provider = EmailPasswordProvider()
    
    async with db.session() as session:
        # Check if email_password system config already exists
        result = await session.execute(
            select(ConfigurationModel).where(
                ConfigurationModel.category == ep_provider.category,
                ConfigurationModel.account_id == SYSTEM_ACCOUNT_ID,
                ConfigurationModel.provider_name == ep_provider.provider_name,
                ConfigurationModel.is_system == True
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing is None:
            # Create default email_password configuration
            # Note: config is empty dict, which is currently not encrypted in this direct seed
            # but that's fine for an empty dict. For other providers, we'd need EncryptionService.
            new_config = ConfigurationModel(
                id=str(uuid.uuid4()),
                account_id=SYSTEM_ACCOUNT_ID,
                category=ep_provider.category,
                provider_name=ep_provider.provider_name,
                display_name=ep_provider.display_name,
                config={}, # Empty config
                enabled=True,
                is_builtin=True,
                is_system=True,
                priority=0
            )
            session.add(new_config)
            await session.commit()
            logger.info("Seeded default Email/Password configuration")


async def _seed_default_email_templates(db: DatabaseManager) -> None:
    """Seed default email templates if they don't exist.

    Args:
        db: Database manager instance.
    """
    import uuid
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.email_template import EmailTemplateModel
    
    # SYSTEM_ACCOUNT_ID constant
    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
    
    # Default templates
    default_templates = [
        {
            "template_type": "email_verification",
            "locale": "en",
            "subject": "Verify your email address for {{ app_name }}",
            "html_body": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        @media only screen and (max-width: 600px) {
            .container { padding: 10px !important; }
            .button { padding: 10px 20px !important; font-size: 14px !important; }
            h1 { font-size: 24px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px;">
                    <!-- Header -->
                    <tr>
                        <td style="text-align: center; padding-bottom: 30px;">
                            <h1 style="margin: 0; color: #2c3e50; font-size: 28px; font-weight: 600;">{{ app_name }}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td>
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Verify Your Email Address</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Thank you for signing up for {{ app_name }}! To complete your registration and start using your account, please verify your email address by clicking the button below:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ verification_url }}" class="button" style="display: inline-block; background-color: #3498db; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(52,152,219,0.3);">Verify Email Address</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #3498db; font-size: 14px;">{{ verification_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #f7fafc; padding: 16px; border-radius: 6px; border-left: 4px solid #3498db;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Verification Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This verification link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">If you didn't create an account with {{ app_name }}, you can safely ignore this email.</p>
                            <p style="margin: 0; color: #a0aec0; font-size: 13px;">Need help? Visit <a href="{{ app_url }}" style="color: #3498db; text-decoration: none;">{{ app_name }}</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
            """.strip(),
            "text_body": """
{{ app_name }} - Verify Your Email Address

Hello{% if user_name %} {{ user_name }}{% endif %},

Thank you for signing up for {{ app_name }}! To complete your registration and start using your account, please verify your email address by visiting the following link:

{{ verification_url }}

{% if token %}Verification Code: {{ token }}{% endif %}

{% if expires_at %}This verification link will expire on {{ expires_at }}.{% endif %}

If you didn't create an account with {{ app_name }}, you can safely ignore this email.

Need help? Visit {{ app_url }}
            """.strip(),
        },
        {
            "template_type": "password_reset",
            "locale": "en",
            "subject": "Reset your password for {{ app_name }}",
            "html_body": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        @media only screen and (max-width: 600px) {
            .container { padding: 10px !important; }
            .button { padding: 10px 20px !important; font-size: 14px !important; }
            h1 { font-size: 24px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px;">
                    <!-- Header -->
                    <tr>
                        <td style="text-align: center; padding-bottom: 30px;">
                            <h1 style="margin: 0; color: #2c3e50; font-size: 28px; font-weight: 600;">{{ app_name }}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td>
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Reset Your Password</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. Click the button below to create a new password:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ reset_url }}" class="button" style="display: inline-block; background-color: #e74c3c; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(231,76,60,0.3);">Reset Password</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #e74c3c; font-size: 14px;">{{ reset_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #fef5f5; padding: 16px; border-radius: 6px; border-left: 4px solid #e74c3c;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Reset Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This password reset link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Security Warning -->
                    <tr>
                        <td style="padding-top: 20px;">
                            <div style="background-color: #fff5f5; border-left: 4px solid #fc8181; padding: 16px; border-radius: 6px;">
                                <p style="margin: 0 0 8px 0; color: #c53030; font-size: 14px; font-weight: 600;">🔒 Security Notice</p>
                                <p style="margin: 0; color: #742a2a; font-size: 13px; line-height: 1.5;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged. For security, we recommend changing your password if you suspect unauthorized access to your account.</p>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">This password reset was requested from your {{ app_name }} account.</p>
                            <p style="margin: 0; color: #a0aec0; font-size: 13px;">Need help? Visit <a href="{{ app_url }}" style="color: #3498db; text-decoration: none;">{{ app_name }}</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
            """.strip(),
            "text_body": """
{{ app_name }} - Reset Your Password

Hello{% if user_name %} {{ user_name }}{% endif %},

We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. To create a new password, visit the following link:

{{ reset_url }}

{% if token %}Reset Code: {{ token }}{% endif %}

{% if expires_at %}This password reset link will expire on {{ expires_at }}.{% endif %}

SECURITY NOTICE:
If you didn't request a password reset, please ignore this email. Your password will remain unchanged. For security, we recommend changing your password if you suspect unauthorized access to your account.

This password reset was requested from your {{ app_name }} account.

Need help? Visit {{ app_url }}
            """.strip(),
        },
        {
            "template_type": "invitation",
            "locale": "en",
            "subject": "You've been invited to join {{ account_name }} on {{ app_name }}",
            "html_body": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You've Been Invited</title>
    <style>
        @media only screen and (max-width: 600px) {
            .container { padding: 10px !important; }
            .button { padding: 10px 20px !important; font-size: 14px !important; }
            h1 { font-size: 24px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px;">
                    <!-- Header -->
                    <tr>
                        <td style="text-align: center; padding-bottom: 30px;">
                            <h1 style="margin: 0; color: #2c3e50; font-size: 28px; font-weight: 600;">{{ app_name }}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td>
                            <div style="text-align: center; padding: 20px 0;">
                                <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                                <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">You've Been Invited!</h2>
                            </div>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;"><strong style="color: #2c3e50;">{{ invited_by }}</strong> has invited you to join <strong style="color: #2c3e50;">{{ account_name }}</strong> on {{ app_name }}.</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Click the button below to accept this invitation and get started:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ invitation_url }}" class="button" style="display: inline-block; background-color: #27ae60; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(39,174,96,0.3);">Accept Invitation</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #27ae60; font-size: 14px;">{{ invitation_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #f0fdf4; padding: 16px; border-radius: 6px; border-left: 4px solid #27ae60;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Invitation Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- What's Next -->
                    <tr>
                        <td style="padding-top: 30px;">
                            <div style="background-color: #f7fafc; padding: 20px; border-radius: 6px;">
                                <p style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">What happens next?</p>
                                <ul style="margin: 0; padding-left: 20px; color: #4a5568; font-size: 14px; line-height: 1.8;">
                                    <li>Click the button above to accept the invitation</li>
                                    <li>Create your account or sign in if you already have one</li>
                                    <li>Start collaborating with {{ account_name }}</li>
                                </ul>
                            </div>
                        </td>
                    </tr>
                    <!-- Expiration Notice -->
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This invitation will expire in 48 hours. Don't miss out!</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">If you didn't expect this invitation or don't want to join, you can safely ignore this email.</p>
                            <p style="margin: 0; color: #a0aec0; font-size: 13px;">Questions? Visit <a href="{{ app_url }}" style="color: #3498db; text-decoration: none;">{{ app_name }}</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
            """.strip(),
            "text_body": """
{{ app_name }} - You've Been Invited!

Hello{% if user_name %} {{ user_name }}{% endif %},

{{ invited_by }} has invited you to join {{ account_name }} on {{ app_name }}.

To accept this invitation and get started, visit the following link:

{{ invitation_url }}

{% if token %}Invitation Code: {{ token }}{% endif %}

WHAT HAPPENS NEXT?
1. Click the link above to accept the invitation
2. Create your account or sign in if you already have one
3. Start collaborating with {{ account_name }}

This invitation will expire in 48 hours. Don't miss out!

If you didn't expect this invitation or don't want to join, you can safely ignore this email.

Questions? Visit {{ app_url }}
            """.strip(),
        },
    ]
    
    async with db.session() as session:
        for template_data in default_templates:
            # Check if template already exists
            result = await session.execute(
                select(EmailTemplateModel).where(
                    EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
                    EmailTemplateModel.template_type == template_data["template_type"],
                    EmailTemplateModel.locale == template_data["locale"],
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing is None:
                # Create default email template
                new_template = EmailTemplateModel(
                    id=str(uuid.uuid4()),
                    account_id=SYSTEM_ACCOUNT_ID,
                    template_type=template_data["template_type"],
                    locale=template_data["locale"],
                    subject=template_data["subject"],
                    html_body=template_data["html_body"],
                    text_body=template_data["text_body"],
                    enabled=True,
                    is_builtin=True,
                )
                session.add(new_template)
                logger.info(
                    "Seeded default email template",
                    template_type=template_data["template_type"],
                    locale=template_data["locale"],
                )
        
        await session.commit()


async def close_database() -> None:
    """Close the database connection.

    This function should be called on application shutdown.
    """
    db = get_db_manager()
    await db.disconnect()
