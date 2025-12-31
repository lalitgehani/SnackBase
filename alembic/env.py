import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import SnackBase settings and models
from snackbase.core.config import get_settings
from snackbase.infrastructure.persistence.database import Base
from snackbase.infrastructure.persistence import models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support
target_metadata = Base.metadata

# Set the database URL from settings if not provided in config
# IMPORTANT: Always use the async URL here because async_engine_from_config needs it
# Alembic handles the async/sync conversion internally
settings = get_settings()
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True if url and url.startswith("sqlite") else False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True if url and url.startswith("sqlite") else False,
    )

    # Use existing transaction if connection is provided, otherwise start a new one
    if config.attributes.get("connection"):
        context.run_migrations()
    else:
        with context.begin_transaction():
            context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Check if a connection was passed in the configuration attributes
    # This is used by the application and tests to share a connection
    connection = config.attributes.get("connection")

    if connection is not None:
        do_run_migrations(connection)
        return

    # For async support, we need to handle the event loop differently
    # if it's already running (e.g. when called from application code)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # This is used for CLI use when an event loop is already running
        # (e.g. when calling from pytest-asyncio or a long-running app)
        # Note: In production, it's better to run migrations before the loop starts
        asyncio.ensure_future(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
