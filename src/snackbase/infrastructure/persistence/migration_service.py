"""Migration service for managing dynamic collection migrations.

Uses Alembic programmatic API to generate and apply migrations for user-defined collections.
"""

import os
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


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
        dynamic_dir = os.path.abspath("sb_data/migrations")
        
        # Generate the revision
        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
        )
        
        # Now we need to find the file and inject the DDL
        # Alembic revision() returns the Script object in latest versions
        rev_id = rev.revision
        filename = f"{rev_id}_{message.lower()}.py"
        filepath = os.path.join(dynamic_dir, filename)
        
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
        dynamic_dir = os.path.abspath("sb_data/migrations")
        
        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
        )
        
        rev_id = rev.revision
        filename = f"{rev_id}_{message.lower()}.py"
        filepath = os.path.join(dynamic_dir, filename)
        
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
        dynamic_dir = os.path.abspath("sb_data/migrations")
        
        rev = command.revision(
            self.config,
            message=message,
            autogenerate=False,
            version_path=dynamic_dir,
        )
        
        rev_id = rev.revision
        filename = f"{rev_id}_{message.lower()}.py"
        filepath = os.path.join(dynamic_dir, filename)
        
        upgrade_lines = self._generate_drop_table_op_lines(collection_name)
        # Downgrade for drop table is hard because we'd need the full old schema.
        # For now, we'll leave downgrade empty or just log a warning.
        downgrade_lines = [
            f"    # Downgrade for delete_collection_{collection_name} is not supported",
            "    pass"
        ]
        
        self._inject_ops_into_migration(filepath, upgrade_lines, downgrade_lines)
        
        return rev_id

    async def apply_migrations(self, connection: Any = None) -> None:
        """Apply all pending migrations to the database.

        Args:
            connection: Optional existing AsyncConnection to use.
        """
        if connection:
            def run_upgrade(sync_conn):
                self.config.attributes["connection"] = sync_conn
                command.upgrade(self.config, "head")
            await connection.run_sync(run_upgrade)
        else:
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, command.upgrade, self.config, "head")

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
        
        # User defined columns
        for field in schema:
            name = field["name"]
            f_type = field["type"].lower()
            sql_type = self._map_to_sa_type(f_type)
            
            nullable = not field.get("required", False)
            unique = field.get("unique", False)
            default = field.get("default")
            
            col_part = f"        sa.Column('{name}', {sql_type}, nullable={nullable}, unique={unique}"
            if default is not None:
                if isinstance(default, str):
                    col_part += f", server_default=sa.text(\"'{default}'\")"
                elif isinstance(default, bool):
                     col_part += f", server_default=sa.text('{1 if default else 0}')"
                else:
                    col_part += f", server_default=sa.text('{default}')"
            col_part += "),"
            lines.append(col_part)
            
        # Foreign Keys
        for field in schema:
            if field["type"].lower() == "reference":
                name = field["name"]
                target = TableBuilder.generate_table_name(field.get("collection", ""))
                on_delete = field.get("on_delete", "RESTRICT").upper()
                lines.append(f"        sa.ForeignKeyConstraint(['{name}'], ['{target}.id'], ondelete='{on_delete}'),")
                
        lines.append("    )")
        
        # Indexes
        lines.append(f"    op.create_index('ix_{table_name}_account_id', '{table_name}', ['account_id'])")
        for field in schema:
            if field["type"].lower() == "reference":
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
            name = field["name"]
            f_type = field["type"].lower()
            sql_type = self._map_to_sa_type(f_type)
            nullable = not field.get("required", False)
            unique = field.get("unique", False)
            default = field.get("default")
            
            col_part = f"        batch_op.add_column(sa.Column('{name}', {sql_type}, nullable={nullable}, unique={unique}"
            if default is not None:
                if isinstance(default, str):
                    col_part += f", server_default=sa.text(\"'{default}'\")"
                elif isinstance(default, bool):
                     col_part += f", server_default=sa.text('{1 if default else 0}')"
                else:
                    col_part += f", server_default=sa.text('{default}')"
            col_part += "))"
            lines.append(col_part)
            
            # Index if reference
            if f_type == "reference":
                lines.append(f"        batch_op.create_index('ix_{table_name}_{name}', ['{name}'])")
                
        return lines

    def _generate_remove_columns_op_lines(self, collection_name: str, fields: list[dict[str, Any]]) -> list[str]:
        table_name = TableBuilder.generate_table_name(collection_name)
        lines = [f"    with op.batch_alter_table('{table_name}', schema=None) as batch_op:"]
        for field in fields:
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
        }
        return mapping.get(field_type, "sa.Text()")

    def _inject_ops_into_migration(self, filepath: str, upgrade_lines: list[str], downgrade_lines: list[str]) -> None:
        with open(filepath, "r") as f:
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
            if idx == -1: return text
            
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
