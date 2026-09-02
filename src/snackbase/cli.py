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
@click.version_option(version="0.11.0", prog_name="SnackBase")
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
    command.upgrade(alembic_cfg, "heads")
    click.echo("Migrations applied successfully.")

    # Step 3: Seed default roles and permissions
    async def seed_data():
        db = get_db_manager()

        # Seed default roles
        click.echo("Seeding default roles...")
        from snackbase.infrastructure.persistence.database import _seed_default_roles
        await _seed_default_roles(db, RoleModel)
        click.echo("Default roles seeded.")

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
    from snackbase.domain.services import SuperadminCreationError, SuperadminService
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
    default="heads",
    help="Target revision (default: heads — applies all branch heads)",
)
def upgrade(revision: str) -> None:
    """Apply pending migrations across all branches (core and dynamic)."""
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


@migrate.command()
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing files.")
def repair(dry_run: bool) -> None:
    """Repair legacy dynamic migrations to use Alembic branch labels.

    Run this once after upgrading from a SnackBase version that used a single
    linear migration chain.  It rewrites any dynamic migration files in
    sb_data/migrations/ so that:

    \b
    - The earliest dynamic migration gets branch_labels = ('dynamic',),
      down_revision = None, and depends_on = (<core rev it originally chained from>)
    - All other dynamic migrations are left untouched (they already chain within
      the dynamic branch)

    The core migration chain in alembic/versions/ is never touched.
    """
    import re
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_cfg = Config("alembic.ini")
    script_dir = ScriptDirectory.from_config(alembic_cfg)

    dynamic_dir = Path("sb_data/migrations")
    if not dynamic_dir.exists():
        click.echo("No sb_data/migrations/ directory found — nothing to repair.")
        return

    # Collect all dynamic revision objects (by module path)
    dynamic_revs = [
        rev
        for rev in script_dir.walk_revisions()
        if rev.module and "sb_data" in (rev.module.__file__ or "")
    ]

    if not dynamic_revs:
        click.echo("No dynamic migrations found — nothing to repair.")
        return

    # Check if already using branch labels
    already_branched = any("dynamic" in (rev.branch_labels or set()) for rev in dynamic_revs)
    if already_branched:
        click.echo("Dynamic migrations already use branch labels — nothing to repair.")
        return

    # Find the root of the dynamic chain (the one whose down_revision points to a core rev)
    # Build a set of all dynamic revision IDs
    dynamic_ids = {rev.revision for rev in dynamic_revs}

    # The root dynamic migration is the one whose down_revision is NOT another dynamic rev
    roots = [rev for rev in dynamic_revs if rev.down_revision not in dynamic_ids]
    if len(roots) != 1:
        click.echo(
            f"Expected exactly one root dynamic migration, found {len(roots)}: "
            f"{[r.revision for r in roots]}\nAborting — manual intervention required.",
            err=True,
        )
        raise SystemExit(1)

    root = roots[0]
    original_down_revision = root.down_revision
    click.echo(
        f"Root dynamic migration : {root.revision} ({root.doc})\n"
        f"  Currently chains from: {original_down_revision} (core migration)\n"
        f"  Will be rewritten to  : branch_labels=('dynamic',), "
        f"down_revision=None, depends_on=('{original_down_revision}',)"
    )

    if dry_run:
        click.echo("\n[dry-run] No files were modified.")
        return

    # Rewrite the root migration file
    filepath = Path(root.path)
    content = filepath.read_text()

    # Replace down_revision value
    content = re.sub(
        r"^(down_revision\s*:\s*.*?=\s*).*$",
        r"\g<1>None",
        content,
        flags=re.MULTILINE,
    )
    # Replace branch_labels value
    content = re.sub(
        r"^(branch_labels\s*:\s*.*?=\s*).*$",
        r"\g<1>('dynamic',)",
        content,
        flags=re.MULTILINE,
    )
    # Replace depends_on value
    content = re.sub(
        r"^(depends_on\s*:\s*.*?=\s*).*$",
        rf"\g<1>('{original_down_revision}',)",
        content,
        flags=re.MULTILINE,
    )

    filepath.write_text(content)
    click.echo(f"  Rewrote: {filepath}")
    click.echo(
        "\nRepair complete.  Run 'migrate upgrade' to apply any pending migrations."
    )


@cli.command()
@click.option(
    "--queue",
    type=str,
    default=None,
    help="Only process jobs from this queue (default: all queues)",
)
@click.option(
    "--poll-interval",
    type=float,
    default=None,
    help="Override poll interval in seconds (default: from config)",
)
def worker(queue: str | None, poll_interval: float | None) -> None:
    """Start a standalone background job worker process.

    For multi-process deployments, run this command separately from the
    web server. The worker polls the database for pending jobs and executes
    them reliably with retry support and exponential backoff.

    Examples:

        # Process all queues
        python -m snackbase worker

        # Process only the 'webhooks' queue
        python -m snackbase worker --queue webhooks

        # Override poll interval
        python -m snackbase worker --poll-interval 0.5
    """
    import asyncio

    settings = get_settings()
    configure_logging(settings)

    logger = get_logger(__name__)

    async def run() -> None:
        from snackbase.infrastructure.backup.restore import (
            RestoreAbortedError,
            execute_pending_restore,
        )
        from snackbase.infrastructure.persistence.database import (
            get_db_manager,
            init_database,
        )
        from snackbase.infrastructure.services.job_service import JobWorker

        # Perform any pending restore before the database is opened, so a
        # worker-only process cannot boot against half-restored data (F3.2).
        try:
            execute_pending_restore(settings)
        except RestoreAbortedError as exc:
            click.echo(f"Error: pending restore failed: {exc}", err=True)
            raise SystemExit(1) from exc

        # Initialize database
        await init_database()
        db_manager = get_db_manager()

        # Import job_service module to trigger handler registration side-effects
        import snackbase.infrastructure.services.job_service  # noqa: F401

        # Allow CLI override of poll interval
        effective_settings = settings
        if poll_interval is not None:
            # Create a lightweight wrapper to override the poll interval
            class _SettingsOverride:
                def __getattr__(self, name: str):  # type: ignore[override]
                    if name == "job_worker_poll_interval":
                        return poll_interval
                    return getattr(effective_settings, name)

            effective_settings = _SettingsOverride()  # type: ignore[assignment]

        job_worker = JobWorker(
            session_factory=db_manager.session,
            settings=effective_settings,
            queue_filter=queue,
        )
        await job_worker.start()
        logger.info(
            "Standalone job worker started",
            queue_filter=queue,
            poll_interval=poll_interval or settings.job_worker_poll_interval,
        )

        try:
            # Run until interrupted
            stop_event = asyncio.Event()
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await job_worker.stop()
            await db_manager.disconnect()

    click.echo("Starting SnackBase job worker... (Ctrl+C to stop)")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nJob worker stopped.")


@cli.group("functions")
def functions_group() -> None:
    """Manage and deploy SnackBase Functions."""


@functions_group.command("list")
@click.option("--url", envvar="SNACKBASE_URL", default="http://127.0.0.1:8090")
@click.option("--token", envvar="SNACKBASE_TOKEN", required=True, help="Bearer access token")
def functions_list(url: str, token: str) -> None:
    """List remote functions for the authenticated account."""
    import httpx

    resp = httpx.get(
        f"{url.rstrip('/')}/api/v1/functions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise click.ClickException(f"List failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    for item in data.get("items", []):
        click.echo(
            f"{item.get('slug'):<24} enabled={item.get('enabled')} "
            f"auth={item.get('auth_required')} status={item.get('status')}"
        )
    click.echo(f"Total: {data.get('total', 0)}")


@functions_group.command("deploy")
@click.argument("slug")
@click.option(
    "--dir",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=str),
    default=None,
    help="Directory with handler.py / requirements.txt (default: snackbase/functions/<slug>)",
)
@click.option("--url", envvar="SNACKBASE_URL", default="http://127.0.0.1:8090")
@click.option("--token", envvar="SNACKBASE_TOKEN", required=True)
def functions_deploy(slug: str, source_dir: str | None, url: str, token: str) -> None:
    """Deploy a local function directory to the instance."""
    from pathlib import Path

    import httpx

    root = Path(source_dir) if source_dir else Path("snackbase/functions") / slug
    if not root.exists():
        raise click.ClickException(f"Source directory not found: {root}")

    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file() and not any(p.startswith(".") for p in path.parts):
            rel = path.relative_to(root).as_posix()
            files[rel] = path.read_text(encoding="utf-8")
    if not files:
        raise click.ClickException("No source files found to deploy")

    deps: list[str] = []
    req = root / "requirements.txt"
    if req.exists():
        deps = [
            line.strip()
            for line in req.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    headers = {"Authorization": f"Bearer {token}"}
    base = url.rstrip("/")
    # Ensure function exists
    get_resp = httpx.get(f"{base}/api/v1/functions/{slug}", headers=headers, timeout=30.0)
    if get_resp.status_code == 404:
        create = httpx.post(
            f"{base}/api/v1/functions",
            headers=headers,
            json={"name": slug, "slug": slug},
            timeout=30.0,
        )
        if create.status_code >= 400:
            raise click.ClickException(f"Create failed: {create.text}")

    deploy = httpx.post(
        f"{base}/api/v1/functions/{slug}/deploy",
        headers=headers,
        json={"files": files, "dependencies": deps},
        timeout=300.0,
    )
    if deploy.status_code >= 400:
        raise click.ClickException(f"Deploy failed ({deploy.status_code}): {deploy.text}")
    version = deploy.json().get("version", {})
    click.echo(f"Deployed {slug} version {version.get('version')} sha={version.get('sha256')}")


@functions_group.command("logs")
@click.argument("slug")
@click.option("--url", envvar="SNACKBASE_URL", default="http://127.0.0.1:8090")
@click.option("--token", envvar="SNACKBASE_TOKEN", required=True)
@click.option("--limit", default=20, show_default=True)
def functions_logs(slug: str, url: str, token: str, limit: int) -> None:
    """Print recent function executions."""
    import httpx

    resp = httpx.get(
        f"{url.rstrip('/')}/api/v1/functions/{slug}/executions",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": limit},
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise click.ClickException(f"Logs failed ({resp.status_code}): {resp.text}")
    for item in resp.json().get("items", []):
        click.echo(
            f"{item.get('executed_at')}  {item.get('status'):<8} "
            f"http={item.get('http_status')}  {item.get('duration_ms')}ms  "
            f"{item.get('error_message') or ''}"
        )


@functions_group.command("serve")
@click.argument("slug")
@click.option(
    "--dir",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=str),
    default=None,
)
@click.option("--url", envvar="SNACKBASE_URL", default="http://127.0.0.1:8090")
@click.option("--token", envvar="SNACKBASE_TOKEN", default=None)
def functions_serve(slug: str, source_dir: str | None, url: str, token: str | None) -> None:
    """Watch a local function directory and redeploy on change (requires token)."""
    import time
    from pathlib import Path

    if not token:
        raise click.ClickException("SNACKBASE_TOKEN is required for functions serve")

    root = Path(source_dir) if source_dir else Path("snackbase/functions") / slug
    if not root.exists():
        raise click.ClickException(f"Source directory not found: {root}")

    click.echo(f"Watching {root} — redeploying to {url} as {slug} (Ctrl+C to stop)")
    last_mtime = 0.0
    ctx = click.get_current_context()
    while True:
        try:
            mtimes = [p.stat().st_mtime for p in root.rglob("*") if p.is_file()]
            newest = max(mtimes) if mtimes else 0.0
            if newest > last_mtime:
                last_mtime = newest
                ctx.invoke(
                    functions_deploy,
                    slug=slug,
                    source_dir=str(root),
                    url=url,
                    token=token,
                )
            time.sleep(1.0)
        except KeyboardInterrupt:
            click.echo("\nStopped watching.")
            break


@functions_group.command("purge-executions")
def functions_purge_executions() -> None:
    """Purge function execution logs older than retention config (local DB)."""
    import asyncio

    from snackbase.infrastructure.functions.retention import purge_old_function_executions
    from snackbase.infrastructure.persistence.database import get_db_manager

    async def _run() -> int:
        db = get_db_manager()
        async with db.session() as session:
            return await purge_old_function_executions(session)

    deleted = asyncio.run(_run())
    click.echo(f"Deleted {deleted} old function executions")


@cli.group()
def backup() -> None:
    """Manage instance backups (archives of database and local files).

    Commands operate directly against the configured destination without
    requiring a running server, so they can be cron-driven independently of
    the in-app scheduler.
    """


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{size:.1f}TB"  # pragma: no cover - unreachable


@backup.command("create")
@click.option(
    "--name",
    type=str,
    default=None,
    help="Archive name (default: snackbase_backup_<UTC timestamp>.zip)",
)
@click.option(
    "--type",
    "backup_type",
    type=click.Choice(["logical", "sqlite_physical"]),
    default=None,
    help="Archive type (default: engine chooses; PostgreSQL produces logical)",
)
def backup_create(name: str | None, backup_type: str | None) -> None:
    """Create a consistent backup archive at the configured destination."""
    import asyncio

    from snackbase.infrastructure.backup.destinations import (
        BackupError,
        resolve_destination,
    )
    from snackbase.infrastructure.backup.service import (
        create_backup,
        generate_backup_name,
        resolve_backup_type,
    )
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)
    archive_name = name or generate_backup_name()
    try:
        archive_type = resolve_backup_type(backup_type, settings.database_url)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    async def run() -> int:
        db = get_db_manager()
        try:
            async with db.session() as session:
                destination = await resolve_destination(session)
            outcome = await create_backup(
                name=archive_name,
                destination=destination,
                session_factory=db.session,
                backup_type=archive_type,
            )
            click.echo(
                f"Created {outcome.name} "
                f"({_human_size(outcome.size)}) at {outcome.destination_type}"
            )
            return 0
        except BackupError as exc:
            click.echo(f"Error: {exc}", err=True)
            return 1
        finally:
            await db.disconnect()

    raise SystemExit(asyncio.run(run()))


@backup.command("list")
def backup_list() -> None:
    """List archives at the configured destination."""
    import asyncio

    from snackbase.infrastructure.backup.destinations import (
        BackupError,
        resolve_destination,
    )
    from snackbase.infrastructure.backup.service import classify_archive
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)

    async def run() -> int:
        db = get_db_manager()
        try:
            async with db.session() as session:
                destination = await resolve_destination(session)
            entries = await destination.list()
            if not entries:
                click.echo("No backups found.")
                return 0
            for entry in entries:
                marker = "auto" if entry.name.startswith("@auto_") else "manual"
                modified = entry.modified.strftime("%Y-%m-%d %H:%M:%S")
                archive_type, restorable = await classify_archive(
                    destination, entry.name
                )
                type_label = archive_type if restorable else f"{archive_type} (portable)"
                click.echo(
                    f"{entry.name:<48} {_human_size(entry.size):>10} "
                    f"{modified:<20} {marker:<7} {type_label}"
                )
            return 0
        except BackupError as exc:
            click.echo(f"Error: {exc}", err=True)
            return 1
        finally:
            await db.disconnect()

    raise SystemExit(asyncio.run(run()))


@backup.command()
@click.argument("name")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompt")
def delete(name: str, yes: bool) -> None:
    """Delete the archive NAME from the configured destination."""
    import asyncio

    from snackbase.infrastructure.backup.audit import write_backup_event
    from snackbase.infrastructure.backup.destinations import (
        BackupError,
        resolve_destination,
    )
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)

    async def run() -> int:
        db = get_db_manager()
        try:
            async with db.session() as session:
                destination = await resolve_destination(session)
            if not yes:
                click.confirm(f"Delete backup {name!r}?", abort=True, default=False)
            await destination.delete(name)
            await write_backup_event(
                db.session,
                event="backup.delete",
                name=name,
                destination_type=type(destination).__name__.replace(
                    "BackupDestination", ""
                ).lower(),
            )
            click.echo(f"Deleted {name}")
            return 0
        except BackupError as exc:
            click.echo(f"Error: {exc}", err=True)
            return 1
        finally:
            await db.disconnect()

    raise SystemExit(asyncio.run(run()))


@backup.command()
@click.argument("name")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Proceed despite warning-severity compatibility issues",
)
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompt")
def restore(name: str, force: bool, yes: bool) -> None:
    """Restore the archive NAME; the swap happens on next start.

    This command validates the archive and writes the pending-restore
    marker — it does not perform the swap itself, so there is exactly one
    restore implementation. A supervised deployment restarts the process
    automatically and the swap runs before the database is opened.
    """
    import asyncio

    from snackbase.infrastructure.backup.destinations import (
        BackupError,
        BackupNotFoundError,
        resolve_destination,
    )
    from snackbase.infrastructure.backup.manifest import fingerprints_from_settings
    from snackbase.infrastructure.backup.restore import (
        RestoreAbortedError,
        check_engine_is_sqlite,
        destination_to_marker_dict,
        validate_restore_candidate,
        write_marker,
    )
    from snackbase.infrastructure.persistence.database import get_db_manager

    settings = get_settings()
    configure_logging(settings)

    async def run() -> int:
        db = get_db_manager()
        try:
            async with db.session() as session:
                destination = await resolve_destination(session)

            try:
                validation = validate_restore_candidate(destination, name, settings)
            except BackupNotFoundError as exc:
                click.echo(f"Error: {exc}", err=True)
                return 1
            except ValueError as exc:
                click.echo(f"Error: {exc}", err=True)
                return 1

            try:
                check_engine_is_sqlite(settings)
            except RestoreAbortedError as exc:
                click.echo(f"Error: {exc}", err=True)
                return 1

            manifest = validation.manifest
            click.echo(f"Archive:              {name}")
            click.echo(f"Created:              {manifest.created_at}")
            click.echo(f"Source SnackBase:     {manifest.snackbase_version}")
            click.echo(f"Includes files:       {'yes' if manifest.includes_files else 'no'}")
            click.echo(f"Database engine:      {manifest.database_engine}")
            for issue in validation.blocking:
                click.echo(f"BLOCKING: {issue.message}", err=True)
            for issue in validation.warnings:
                click.echo(f"WARNING:  {issue.message}")

            if validation.blocking:
                click.echo(
                    "Restore refused: blocking compatibility issues cannot be overridden.",
                    err=True,
                )
                return 1
            if validation.warnings and not force:
                click.echo(
                    "Restore refused due to compatibility warnings. "
                    "Re-run with --force to proceed anyway.",
                    err=True,
                )
                return 1

            if not yes:
                click.confirm(
                    f"All data created after {manifest.created_at} will be "
                    "discarded and the instance will restart. Continue?",
                    abort=True,
                    default=False,
                )

            write_marker(
                settings,
                archive_name=name,
                destination=destination_to_marker_dict(destination, settings),
                requested_by="system",
                manifest_fingerprints=fingerprints_from_settings(settings),
            )
            click.echo(
                f"\nRestore of {name!r} scheduled.\n"
                "\nThe restore completes on next start; a supervised deployment "
                "restarts automatically.\n"
                "Ensure the container restart policy is 'unless-stopped' or "
                "'always' (docker-compose.yml already sets 'unless-stopped'), "
                "or start the server manually:\n"
                "  python -m snackbase serve"
            )
            return 0
        except BackupError as exc:
            click.echo(f"Error: {exc}", err=True)
            return 1
        finally:
            await db.disconnect()

    raise SystemExit(asyncio.run(run()))


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
