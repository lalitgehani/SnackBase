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
    """Initialize the database.

    Creates all database tables and seeds default data. Use this only in development.
    In production, use migrations instead.
    """
    import asyncio

    from snackbase.infrastructure.persistence.database import (
        get_db_manager,
        init_database,
    )

    settings = get_settings()
    configure_logging(settings)

    if settings.is_production and not force:
        click.echo(
            "ERROR: Running in production mode. Use migrations instead of init_db.",
            err=True,
        )
        raise SystemExit(1)

    if not force:
        click.confirm(
            "This will create all database tables. Continue?",
            abort=True,
            default=False,
        )

    async def initialize():
        try:
            await init_database()
            click.echo("Database initialized successfully.")
        finally:
            db = get_db_manager()
            await db.disconnect()

    asyncio.run(initialize())


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
""")


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
