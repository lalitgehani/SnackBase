"""Command-line interface for SnackBase.

This module provides the CLI commands for running and managing
the SnackBase application.
"""

import sys
from typing import NoReturn

import click

from snackbase.core.config import get_settings
from snackbase.core.logging import configure_logging, get_logger


@click.group()
@click.version_option(version="0.1.0", prog_name="SnackBase")
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file (not yet implemented)",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug mode",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default=None,
    help="Set log level (overrides config file)",
)
def cli(config: str | None, debug: bool, log_level: str | None) -> None:
    """SnackBase - Open-source Backend-as-a-Service.

    A self-hosted alternative to PocketBase with multi-tenancy,
    row-level security, and GxP-compliant audit logging.
    """
    # Note: Settings are loaded via environment variables
    # CLI options can override settings in future implementations


@cli.command()
@click.option(
    "--host",
    type=str,
    default=None,
    help="Host to bind to (overrides config)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Port to bind to (overrides config)",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of worker processes (overrides config)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development",
)
def serve(host: str | None, port: int | None, workers: int | None, reload: bool) -> None:
    """Start the SnackBase server.

    By default, the server runs on 0.0.0.0:8000 with auto-reload
    enabled in development mode.
    """
    import uvicorn

    settings = get_settings()

    # Apply CLI overrides
    bind_host = host or settings.host
    bind_port = port or settings.port
    bind_workers = workers or settings.workers

    # Validate workers for SQLite
    if bind_workers > 1 and settings.database_url.startswith("sqlite"):
        click.echo(
            f"Error: SQLite does not support multiple worker processes. "
            f"Requested {bind_workers} workers, but SQLite requires workers=1. "
            "Either use --workers 1 or switch to PostgreSQL.",
            err=True,
        )
        raise SystemExit(1)

    # Enable auto-reload in development
    if reload is None:
        reload = settings.is_development

    # Configure logging before starting server
    configure_logging(settings)

    logger = get_logger(__name__)
    logger.info(
        "Starting SnackBase server",
        host=bind_host,
        port=bind_port,
        workers=bind_workers,
        reload=reload,
        environment=settings.environment,
    )

    # Run the server
    uvicorn.run(
        "snackbase.infrastructure.api.app:app",
        host=bind_host,
        port=bind_port,
        workers=1 if reload else bind_workers,
        reload=reload,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


@cli.command()
def shell() -> None:
    """Start an interactive Python shell with SnackBase context.

    This provides a REPL with all SnackBase models and utilities
    pre-imported for easy debugging and testing.
    """
    import asyncio
    import os
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)

    banner = f"""
SnackBase Shell v{settings.app_version}
Environment: {settings.environment}
Database: {settings.database_url}

Available objects:
  - settings: Application settings
  - get_db_manager(): Database manager function
  - asyncio: Asyncio module

Example:
    >>> async def test():
    ...     db = get_db_manager()
    ...     return await db.check_connection()
    ... asyncio.run(test())
"""

    # Try to use IPython if available
    try:
        from IPython import start_ipython

        local_vars = {
            "settings": settings,
            "get_db_manager": get_db_manager,
            "asyncio": asyncio,
        }

        start_ipython(argv=[], user_ns=local_vars, banner=banner)
        return

    except ImportError:
        pass

    # Fall back to standard Python REPL
    import code
    import readline

    local_vars = {
        "settings": settings,
        "get_db_manager": get_db_manager,
        "asyncio": asyncio,
    }

    readline.set_completer(code.Completer(local_vars).complete)
    readline.parse_and_bind("tab:complete")

    code.interact(banner=banner, local=local_vars, exitmsg="Exiting SnackBase shell")


@cli.command()
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
def init_db(force: bool) -> None:
    """Initialize the database using Alembic migrations.

    This is a thin wrapper around 'migrate upgrade' that also:
    - Creates the database directory (if using SQLite)
    - Seeds default roles and permissions
    - Creates superadmin from environment variables (if configured)

    For production, use 'migrate upgrade' directly instead.
    """
    import asyncio

    from alembic import command
    from alembic.config import Config
    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.persistence.models import RoleModel

    settings = get_settings()
    configure_logging(settings)

    if settings.is_production and not force:
        click.echo(
            "ERROR: Running in production mode. Use 'migrate upgrade' instead of init_db.",
            err=True,
        )
        raise SystemExit(1)

    if not force:
        click.confirm(
            "This will initialize the database using Alembic migrations and seed default data. Continue?",
            abort=True,
            default=False,
        )

    # Step 1: Create database directory if using SQLite
    if settings.database_url.startswith("sqlite"):
        from pathlib import Path

        db_path = settings.database_url.split(":///")[-1]
        db_file = Path(db_path)
        db_dir = db_file.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Created database directory: {db_dir}")

    # Step 2: Run Alembic migrations
    click.echo("Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    # Note: env.py will set the URL from settings if not provided
    command.upgrade(alembic_cfg, "head")
    click.echo("Migrations applied successfully.")

    # Step 3: Seed default roles and permissions
    async def seed_data():
        db = get_db_manager()

        # Seed default roles
        click.echo("Seeding default roles...")
        from snackbase.infrastructure.persistence.database import _seed_default_roles
        await _seed_default_roles(db, RoleModel)
        click.echo("Default roles seeded.")

        # Seed default permissions
        click.echo("Seeding default permissions...")
        from snackbase.infrastructure.persistence.database import _seed_default_permissions
        await _seed_default_permissions(db)
        click.echo("Default permissions seeded.")

        # Create superadmin from environment variables if configured
        from snackbase.infrastructure.persistence.database import _create_superadmin_from_env
        await _create_superadmin_from_env(db)

        await db.disconnect()

    asyncio.run(seed_data())

    click.echo("\nDatabase initialized successfully!")
    click.echo(f"Database: {settings.database_url}")
    click.echo("\nNext steps:")
    click.echo("  1. Create a superadmin: uv run python -m snackbase create-superadmin")
    click.echo("  2. Start the server:      uv run python -m snackbase serve")


@cli.command()
@click.option(
    "--email",
    type=str,
    default=None,
    help="Superadmin email (prompts if not provided)",
)
@click.option(
    "--password",
    type=str,
    default=None,
    help="Superadmin password (prompts if not provided)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt if superadmin already exists",
)
def create_superadmin(email: str | None, password: str | None, force: bool) -> None:
    """Create a superadmin user.

    Superadmin users have full access to all accounts and system operations.
    The superadmin is linked to the special system account (nil UUID with code SY0000).
    """
    import asyncio

    from snackbase.core.config import get_settings
    from snackbase.core.logging import get_logger
    from snackbase.domain.services import SuperadminService, SuperadminCreationError
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)

    async def create() -> None:
        nonlocal email, password  # Allow modification of outer scope variables
        db = get_db_manager()

        try:
            # Check if superadmin already exists
            async with db.session() as session:
                has_superadmin = await SuperadminService.has_superadmin(session)
            if has_superadmin and not force:
                if not click.confirm(
                    "A superadmin already exists. Do you want to create another one?",
                    default=False,
                ):
                    click.echo("Cancelled.")
                    raise SystemExit(0)

            # Prompt for email if not provided
            if email is None:
                email = click.prompt("Superadmin email", type=str)

            # Validate email format
            if "@" not in email or "." not in email.split("@")[-1]:
                click.echo("Error: Invalid email format", err=True)
                raise SystemExit(1)

            # Prompt for password if not provided
            if password is None:
                password = click.prompt(
                    "Superadmin password",
                    hide_input=True,
                    confirmation_prompt=True,
                )

            # Create superadmin
            try:
                async with db.session() as session:
                    user_id, account_id = await SuperadminService.create_superadmin(
                        email=email,
                        password=password,
                        session=session,
                    )

                # Retrieve account details to get the account_code
                async with db.session() as session:
                    from snackbase.infrastructure.persistence.repositories import (
                        AccountRepository,
                    )

                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(account_id)
                    account_code = account.account_code if account else "Unknown"

                click.echo(
                    f"\nSuperadmin created successfully!\n"
                    f"  User ID:      {user_id}\n"
                    f"  Account ID:   {account_id}\n"
                    f"  Account Code: {account_code}\n"
                    f"  Email:        {email}\n"
                    f"\nYou can now log in using:\n"
                    f"  Account: {account_code} or 'system'\n"
                    f"  Email:   {email}\n"
                )
                logger.info(
                    "Superadmin created via CLI",
                    user_id=user_id,
                    account_id=account_id,
                    account_code=account_code,
                    email=email,
                )
            except SuperadminCreationError as e:
                click.echo(f"Error: {e.message}", err=True)
                logger.error("Superadmin creation failed", error=str(e))
                raise SystemExit(1)
        finally:
            await db.disconnect()

    asyncio.run(create())


@cli.command()
def info() -> None:
    """Display SnackBase configuration and system information."""
    settings = get_settings()

    click.echo(f"""
SnackBase v{settings.app_version}
{'=' * 40}

Configuration:
  Environment:  {settings.environment}
  Debug:        {settings.debug}
  API Prefix:   {settings.api_prefix}

Server:
  Host:         {settings.host}
  Port:         {settings.port}
  Workers:      {settings.workers}

Database:
  URL:          {settings.database_url}
  Pool Size:    {settings.db_pool_size}
  Echo:         {settings.db_echo}

Security:
  Token Expire: {settings.access_token_expire_minutes} minutes
  Refresh Exp:  {settings.refresh_token_expire_days} days

Logging:
  Level:        {settings.log_level}
  Format:       {settings.log_format}

Audit Logging:
  Enabled:      {settings.audit_logging_enabled}
""")


@cli.group()
def migrate() -> None:
    """Database migration management using Alembic."""
    pass


@migrate.command()
@click.option(
    "--revision",
    type=str,
    default="head",
    help="Target revision (default: head)",
)
def upgrade(revision: str) -> None:
    """Apply pending migrations."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    # env.py will set the database URL from settings
    command.upgrade(alembic_cfg, revision)
    click.echo(f"Database upgraded to {revision}")


@migrate.command()
@click.option(
    "--revision",
    type=str,
    default="-1",
    help="Target revision (default: -1)",
)
def downgrade(revision: str) -> None:
    """Roll back migrations."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    # env.py will set the database URL from settings
    command.downgrade(alembic_cfg, revision)
    click.echo(f"Database downgraded to {revision}")


@migrate.command()
@click.option(
    "--message",
    "-m",
    type=str,
    required=True,
    help="Migration description",
)
@click.option(
    "--autogenerate",
    is_flag=True,
    default=True,
    help="Automatically detect schema changes",
)
def revision(message: str, autogenerate: bool) -> None:
    """Create a new migration revision."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    # env.py will set the database URL from settings
    command.revision(alembic_cfg, message=message, autogenerate=autogenerate)
    click.echo(f"Created new migration: {message}")


@migrate.command()
def history() -> None:
    """Show migration history."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.history(alembic_cfg)


@migrate.command()
def current() -> None:
    """Show current revision."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.current(alembic_cfg)


def main() -> NoReturn:
    """Main entry point for the CLI.

    This function is called when the `snackbase` command is run
    or when using `python -m snackbase`.
    """
    cli()


def serve_main() -> NoReturn:
    """Entry point for 'python -m SnackBase serve'."""
    # This allows `python -m snackbase serve` to work
    # The CLI will be invoked with the serve command
    sys.argv[0] = "snackbase"
    if len(sys.argv) == 1:
        sys.argv.append("serve")
    main()


if __name__ == "__main__":
    main()
