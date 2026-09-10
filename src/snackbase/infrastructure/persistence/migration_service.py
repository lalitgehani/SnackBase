"""Migration service for managing dynamic collection migrations.

Uses Alembic programmatic API to generate and apply migrations for user-defined collections.

Branch strategy
---------------
Core migrations live in ``alembic/versions/`` under the ``core`` branch label.
Dynamic (collection) migrations live in ``sb_data/migrations/`` under the ``dynamic``
branch label.  The very first dynamic migration declares ``down_revision = None`` and
``depends_on = (<current core head>,)`` so that Alembic knows core must be applied first
without creating a linear fork in the chain.  Subsequent dynamic migrations chain to the
previous dynamic head inside the ``dynamic`` branch.

This means ``upgrade heads`` applies both branches safely, and new core releases can
extend the ``core`` branch without ever touching the ``dynamic`` branch.
"""

import os
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


def dynamic_migrations_dir(alembic_ini: str | Path = "alembic.ini") -> Path:
    """The instance-volume directory holding dynamic collection migrations.

    Resolved from ``version_locations`` in the Alembic config: the entry that
    is not part of the packaged ``script_location`` tree. Migration
    generation, backup, and restore all resolve the location through this one
    function so the swap cannot drift from where migrations are written.

    When ``SNACKBASE_TEST_DATA_DIR`` is set (the pytest isolation contract),
    revisions are written under that directory instead of the developer
    ``sb_data/migrations`` tree.

    Raises:
        RuntimeError: When ``version_locations`` declares no directory
            outside the packaged script tree.
    """
    test_dir = os.environ.get("SNACKBASE_TEST_DATA_DIR")
    if test_dir:
        path = Path(test_dir) / "migrations"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    ini = Path(alembic_ini)
    cfg = Config(str(ini))
    here = Path(cfg.get_main_option("here") or ini.resolve().parent)

    def _expand(raw: str) -> Path:
        return Path(raw.replace("%(here)s", str(here))).resolve()

    script_location = cfg.get_main_option("script_location")
    script_root = _expand(script_location) if script_location else None
    locations = cfg.get_main_option("version_locations") or ""
    for raw in locations.split(os.pathsep):
        candidate = _expand(raw.strip())
        if not raw.strip():
            continue
        if script_root is not None and (
            candidate == script_root or script_root in candidate.parents
        ):
            continue
        return candidate
    raise RuntimeError(
        "alembic.ini version_locations does not declare a dynamic migrations "
        "directory outside the packaged script_location"
    )


def apply_version_locations(config: Config, alembic_ini: str | Path = "alembic.ini") -> None:
    """Point Alembic at core versions plus ``dynamic_migrations_dir()``."""
    script_location = config.get_main_option("script_location") or "alembic"
    versions = os.path.join(script_location, "versions")
    dyn = str(dynamic_migrations_dir(alembic_ini))
    config.set_main_option("version_locations", os.pathsep.join([versions, dyn]))


class MigrationService:
    """Service for programmatically managing Alembic migrations."""

    def __init__(
        self,
        alembic_ini_path: str = "alembic.ini",
        database_url: str | None = None,
        engine: AsyncEngine | None = None
    ) -> None:
        """Initialize the migration service.

        Args:
            alembic_ini_path: Path to the alembic.ini file.
            database_url: Optional database URL to override the one in alembic.ini.
            engine: Optional database engine to use for migrations.
        """
        self.config = Config(alembic_ini_path)
        self.engine = engine

        # Ensure we use an absolute path for script_location
        script_location = self.config.get_main_option("script_location")
        if script_location and not os.path.isabs(script_location):
            self.config.set_main_option(
                "script_location", os.path.abspath(script_location)
            )

        if database_url:
            self.config.set_main_option("sqlalchemy.url", database_url)
        elif engine:
            # BUG FIX: Use render_as_string(hide_password=False) to ensure password is included
            # Otherwise SQLAlchemy masks it with '***' when converted to string
            self.config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))

        apply_version_locations(self.config, alembic_ini_path)

    def _get_dynamic_branch_args(self) -> dict[str, Any]:
        """Return the Alembic keyword arguments needed to place a new revision in the
        ``dynamic`` branch.

        For the very first dynamic migration the method returns:
            branch_label='dynamic', head='base', depends_on=<core head>

        For subsequent dynamic migrations it simply returns:
            head='dynamic@head'   (chain within the existing dynamic branch)
        """
        script_dir = ScriptDirectory.from_config(self.config)
        # Filter to heads that belong to the dynamic branch
        dynamic_branch_heads = [
            rev
            for rev in script_dir.walk_revisions()
            if "dynamic" in (rev.branch_labels or set())
        ]

        if not dynamic_branch_heads:
            # No dynamic migrations exist yet — start the branch.
            # Use head='base' (global base) so Alembic creates a true root revision.
            # depends_on ensures core is applied first without forking the core chain.
            core_head = script_dir.get_current_head()
            return {
                "branch_label": "dynamic",
                "head": "base",
                "depends_on": core_head,
            }
        else:
            # Continue the existing dynamic branch
            return {
                "head": "dynamic@head",
            }

    def generate_create_collection_migration(
        self, collection_name: str, schema: list[dict[str, Any]]
    ) -> str:
        """Generate a migration for creating a new collection.

        Args:
            collection_name: The name of the collection.
            schema: The collection schema definition.

        Returns:
            The revision ID of the generated migration.
        """
        message = f"create_collection_{collection_name}"

        # We use revision() to generate the skeleton
        # Note: We specify the version path to ensure it goes into sb_data/migrations/
        dynamic_dir = str(dynamic_migrations_dir())
        branch_args = self._get_dynamic_branch_args()

        # Generate the revision
        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
            **branch_args,
        )

        # Now we need to find the file and inject the DDL
        # Alembic revision() returns the Script object in latest versions
        rev_id = rev.revision
        # Use the actual path from the revision object instead of constructing it
        # This ensures we get the correct filename that Alembic generated
        filepath = rev.path

        # Build DDL logic using TableBuilder
        # Note: We translate TableBuilder's DDL to alembic.op calls
        # This is easier than writing raw SQL in op.execute()

        upgrade_lines = self._generate_create_table_op_lines(collection_name, schema)
        downgrade_lines = self._generate_drop_table_op_lines(collection_name)

        self._inject_ops_into_migration(filepath, upgrade_lines, downgrade_lines)

        return rev_id

    def generate_update_collection_migration(
        self, collection_name: str, new_fields: list[dict[str, Any]]
    ) -> str:
        """Generate a migration for adding columns to an existing collection.

        Args:
            collection_name: The name of the collection.
            new_fields: The new fields to add.

        Returns:
            The revision ID of the generated migration.
        """
        message = f"update_collection_{collection_name}"
        dynamic_dir = str(dynamic_migrations_dir())
        branch_args = self._get_dynamic_branch_args()

        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
            **branch_args,
        )

        rev_id = rev.revision
        # Use the actual path from the revision object
        filepath = rev.path

        upgrade_lines = self._generate_add_columns_op_lines(collection_name, new_fields)
        # Downgrade for adding columns is dropping them,
        # but SQLite doesn't support DROP COLUMN in older versions.
        # Alembic's batch_alter_table handles this by recreating the table.
        downgrade_lines = self._generate_remove_columns_op_lines(collection_name, new_fields)

        self._inject_ops_into_migration(filepath, upgrade_lines, downgrade_lines)

        return rev_id

    def generate_delete_collection_migration(self, collection_name: str) -> str:
        """Generate a migration for dropping a collection table.

        Args:
            collection_name: The name of the collection.

        Returns:
            The revision ID of the generated migration.
        """
        message = f"delete_collection_{collection_name}"
        dynamic_dir = str(dynamic_migrations_dir())
        branch_args = self._get_dynamic_branch_args()

        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
            **branch_args,
        )

        rev_id = rev.revision
        # Use the actual path from the revision object
        filepath = rev.path

        upgrade_lines = self._generate_drop_table_op_lines(collection_name)
        # Downgrade for drop table is hard because we'd need the full old schema.
        # For now, we'll leave downgrade empty or just log a warning.
        downgrade_lines = [
            f"    # Downgrade for delete_collection_{collection_name} is not supported",
            "    pass"
        ]

        self._inject_ops_into_migration(filepath, upgrade_lines, downgrade_lines)

        return rev_id

    def generate_plan_migration(
        self,
        plan: dict[str, list[dict[str, Any]]],
        declared: dict[str, list[dict[str, Any]]],
        current: dict[str, list[dict[str, Any]]],
    ) -> str:
        """Write one Alembic revision implementing a schema plan.

        Type changes use add-column / backfill / drop-column rather than
        in-place ``ALTER TYPE``.
        """
        message = "declarative_schema_sync"
        dynamic_dir = str(dynamic_migrations_dir())
        branch_args = self._get_dynamic_branch_args()
        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
            **branch_args,
        )
        rev_id = rev.revision
        filepath = rev.path

        upgrade_lines = self._generate_plan_upgrade_lines(plan, declared, current)
        downgrade_lines = ["    # Declarative schema sync is not reversed automatically", "    pass"]
        self._inject_ops_into_migration(filepath, upgrade_lines, downgrade_lines)
        return rev_id

    def _generate_plan_upgrade_lines(
        self,
        plan: dict[str, list[dict[str, Any]]],
        declared: dict[str, list[dict[str, Any]]],
        current: dict[str, list[dict[str, Any]]],
    ) -> list[str]:
        lines: list[str] = []
        current_names = set(current)
        declared_names = set(declared)

        for collection in sorted(declared_names - current_names):
            lines.extend(self._generate_create_table_op_lines(collection, declared[collection]))

        added_by_collection: dict[str, list[dict[str, Any]]] = {}
        for item in plan.get("added", []):
            collection = item["collection"]
            if collection not in current_names:
                continue
            field_name = item["field"]
            field_def = next(
                (f for f in declared.get(collection, []) if f.get("name") == field_name),
                {"name": field_name, "type": item.get("type") or "text"},
            )
            added_by_collection.setdefault(collection, []).append(field_def)
        for collection, fields in added_by_collection.items():
            lines.extend(self._generate_add_columns_op_lines(collection, fields))

        for item in plan.get("changed", []):
            if item.get("from") == item.get("to") and item.get("destructive"):
                # unique-constraint addition
                collection = item["collection"]
                field_name = item["field"]
                table_name = TableBuilder.generate_table_name(collection)
                lines.append(
                    f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"
                )
                lines.append(
                    f"        batch_op.create_unique_constraint("
                    f"'uq_{table_name}_{field_name}', ['{field_name}'])"
                )
                continue
            collection = item["collection"]
            field_name = item["field"]
            new_type = item.get("to") or "text"
            table_name = TableBuilder.generate_table_name(collection)
            sql_type = self._map_to_sa_type(new_type)
            tmp = f"{field_name}__new"
            lines.append(
                f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"
            )
            lines.append(
                f"        batch_op.add_column(sa.Column('{tmp}', {sql_type}, nullable=True))"
            )
            lines.append(
                f"    op.execute('UPDATE \"{table_name}\" SET \"{tmp}\" = \"{field_name}\"')"
            )
            lines.append(
                f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"
            )
            lines.append(f"        batch_op.drop_column('{field_name}')")
            lines.append(
                f"        batch_op.alter_column('{tmp}', new_column_name='{field_name}')"
            )

        removed_by_collection: dict[str, list[dict[str, Any]]] = {}
        for item in plan.get("removed", []):
            collection = item["collection"]
            if collection not in declared_names:
                continue
            removed_by_collection.setdefault(collection, []).append(
                {"name": item["field"], "type": item.get("type") or "text"}
            )
        for collection, fields in removed_by_collection.items():
            lines.extend(self._generate_remove_columns_op_lines(collection, fields))

        if not lines:
            return ["    pass"]
        return lines

    async def apply_migrations(self, connection: Any = None) -> None:
        """Apply all pending migrations to the database.

        Args:
            connection: Optional existing AsyncConnection to use.
        """
        if connection:
            def run_upgrade(sync_conn):
                self.config.attributes["connection"] = sync_conn
                command.upgrade(self.config, "heads")
            await connection.run_sync(run_upgrade)
        else:
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, command.upgrade, self.config, "heads")

    async def stamp(self, revision: str, connection: Any = None) -> None:
        """Stamp the database with a specific Alembic revision.

        Args:
            revision: The revision ID to stamp to (e.g., 'head', 'base', or a specific ID).
            connection: Optional existing AsyncConnection to use.
        """
        if connection:
            def run_stamp(sync_conn):
                self.config.attributes["connection"] = sync_conn
                command.stamp(self.config, revision)
            await connection.run_sync(run_stamp)
        else:
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, command.stamp, self.config, revision)

    def _generate_create_table_op_lines(self, collection_name: str, schema: list[dict[str, Any]]) -> list[str]:
        table_name = TableBuilder.generate_table_name(collection_name)
        lines = [f"    op.create_table('{table_name}',"]

        # System columns - hardcoded for Alembic migration generation
        # Using standard SQLAlchemy types that work across dialects

        lines.append("        sa.Column('id', sa.String(36), primary_key=True),")
        lines.append("        sa.Column('account_id', sa.String(36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),")
        lines.append("        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),")
        lines.append("        sa.Column('created_by', sa.Text(), nullable=False),")
        lines.append("        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),")
        lines.append("        sa.Column('updated_by', sa.Text(), nullable=False),")

        # User defined columns (skip computed fields — no physical column)
        for field in schema:
            f_type = field["type"].lower()
            if f_type == "computed":
                continue
            name = field["name"]
            sql_type = self._map_to_sa_type(f_type)

            nullable = not field.get("required", False)
            unique = field.get("unique", False)
            default = field.get("default")

            col_part = f"        sa.Column('{name}', {sql_type}, nullable={nullable}, unique={unique}"
            if default is not None:
                if isinstance(default, str):
                    col_part += f", server_default=sa.text(\"'{default}'\")"
                elif isinstance(default, bool):
                    # Use sa.true()/sa.false() for dialect-agnostic boolean defaults
                    col_part += ", server_default=sa.true()" if default else ", server_default=sa.false()"
                else:
                    col_part += f", server_default=sa.text('{default}')"
            col_part += "),"
            lines.append(col_part)

        # Foreign Keys (computed fields have no FK constraints)
        for field in schema:
            ftype = field["type"].lower()
            if ftype == "reference":
                name = field["name"]
                target = TableBuilder.generate_table_name(field.get("collection", ""))
                on_delete = (field.get("on_delete") or "RESTRICT").upper().replace("_", " ")
                lines.append(
                    f"        sa.ForeignKeyConstraint(['{name}'], ['{target}.id'], "
                    f"ondelete='{on_delete}'),"
                )

        lines.append("    )")

        # Indexes (skip computed fields — no physical column)
        lines.append(f"    op.create_index('ix_{table_name}_account_id', '{table_name}', ['account_id'])")
        for field in schema:
            if field["type"].lower() in {"reference", "user"}:
                name = field["name"]
                lines.append(f"    op.create_index('ix_{table_name}_{name}', '{table_name}', ['{name}'])")

        return lines

    def _generate_drop_table_op_lines(self, collection_name: str) -> list[str]:
        table_name = TableBuilder.generate_table_name(collection_name)
        return [f"    op.drop_table('{table_name}')"]

    def _generate_add_columns_op_lines(self, collection_name: str, fields: list[dict[str, Any]]) -> list[str]:
        table_name = TableBuilder.generate_table_name(collection_name)
        lines = [f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"]

        for field in fields:
            f_type = field["type"].lower()
            # Computed fields are virtual — no physical column to add
            if f_type == "computed":
                continue
            name = field["name"]
            sql_type = self._map_to_sa_type(f_type)
            nullable = not field.get("required", False)
            unique = field.get("unique", False)
            default = field.get("default")

            col_part = f"        batch_op.add_column(sa.Column('{name}', {sql_type}, nullable={nullable}, unique={unique}"
            if default is not None:
                if isinstance(default, str):
                    col_part += f", server_default=sa.text(\"'{default}'\")"
                elif isinstance(default, bool):
                    # Use sa.true()/sa.false() for dialect-agnostic boolean defaults
                    col_part += ", server_default=sa.true()" if default else ", server_default=sa.false()"
                else:
                    col_part += f", server_default=sa.text('{default}')"
            col_part += "))"
            lines.append(col_part)

            # Index if reference or user
            if f_type in {"reference", "user"}:
                lines.append(f"        batch_op.create_index('ix_{table_name}_{name}', ['{name}'])")

        return lines

    def _generate_remove_columns_op_lines(self, collection_name: str, fields: list[dict[str, Any]]) -> list[str]:
        table_name = TableBuilder.generate_table_name(collection_name)
        lines = [f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"]
        for field in fields:
            # Computed fields have no physical column to drop
            if field.get("type", "").lower() == "computed":
                continue
            name = field["name"]
            lines.append(f"        batch_op.drop_column('{name}')")
        return lines

    def _map_to_sa_type(self, field_type: str) -> str:
        mapping = {
            "text": "sa.Text()",
            "number": "sa.Float()",
            "boolean": "sa.Boolean()",
            "datetime": "sa.DateTime()",
            "email": "sa.String(255)",
            "url": "sa.String(500)",
            "json": "sa.JSON()",
            "reference": "sa.String(36)",
            "user": "sa.String(36)",
            "file": "sa.Text()",
            "date": "sa.Date()",
        }
        return mapping.get(field_type, "sa.Text()")

    def _inject_ops_into_migration(self, filepath: str, upgrade_lines: list[str], downgrade_lines: list[str]) -> None:
        with open(filepath) as f:
            content = f.read()

        # Ensure pass is added if lines are empty
        if not upgrade_lines:
            upgrade_lines = ["    pass"]
        if not downgrade_lines:
            downgrade_lines = ["    pass"]

        # Also ensure sa and op are imported if not present
        # Most Alembic templates include them, but let's be safe
        if "import sqlalchemy as sa" not in content:
            content = "import sqlalchemy as sa\n" + content
        if "from alembic import op" not in content:
            content = "from alembic import op\n" + content

        upgrade_marker = "def upgrade() -> None:"
        downgrade_marker = "def downgrade() -> None:"

        def insert_body(text, marker, body_lines):
            idx = text.find(marker)
            if idx == -1:
                return text

            func_end = text.find(":", idx) + 1
            next_line = text.find("\n", func_end) + 1

            placeholder = "    # ### commands auto generated by Alembic - please adjust! ###"
            placeholder_idx = text.find(placeholder, next_line)

            if placeholder_idx != -1:
                start_injection = text.find("\n", placeholder_idx) + 1
                end_marker = "    # ### end Alembic commands ###"
                end_idx = text.find(end_marker, start_injection)

                if end_idx != -1:
                    return text[:start_injection] + "\n".join(body_lines) + "\n" + text[end_idx:]

            next_def = text.find("def ", next_line)
            if next_def == -1:
                return text[:next_line] + "\n".join(body_lines) + "\n"
            else:
                return text[:next_line] + "\n".join(body_lines) + "\n\n" + text[next_def:]

        new_content = insert_body(content, upgrade_marker, upgrade_lines)
        new_content = insert_body(new_content, downgrade_marker, downgrade_lines)

        with open(filepath, "w") as f:
            f.write(new_content)
