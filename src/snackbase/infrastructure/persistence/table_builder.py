"""Dynamic table builder for creating physical tables from collection schemas.

Generates DDL and creates tables for user-defined collections.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.core.logging import get_logger
from snackbase.domain.services import FieldType, OnDeleteAction

logger = get_logger(__name__)


# SQL type mapping for each field type
FIELD_TYPE_TO_SQL = {
    FieldType.TEXT.value: "TEXT",
    FieldType.NUMBER.value: "REAL",
    FieldType.BOOLEAN.value: "INTEGER",  # 0/1 for SQLite compatibility
    FieldType.DATETIME.value: "DATETIME",
    FieldType.EMAIL.value: "TEXT",
    FieldType.URL.value: "TEXT",
    FieldType.JSON.value: "TEXT",  # JSON stored as TEXT for SQLite
    FieldType.REFERENCE.value: "TEXT",  # Reference stored as TEXT (foreign key ID)
    FieldType.FILE.value: "TEXT",  # File metadata stored as JSON TEXT
    FieldType.DATE.value: "DATE",
}

# System columns auto-added to every collection table
SYSTEM_COLUMNS = [
    ("id", "TEXT PRIMARY KEY"),
    ("account_id", "VARCHAR(36) NOT NULL REFERENCES accounts(id) ON DELETE CASCADE"),
    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("created_by", "TEXT NOT NULL"),
    ("updated_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("updated_by", "TEXT NOT NULL"),
]


class TableBuilder:
    """Builds and creates physical database tables from collection schemas."""

    @classmethod
    def generate_table_name(cls, collection_name: str) -> str:
        """Generate a unique table name from collection name.

        Prefixes with 'col_' to distinguish from system tables and ensure
        uniqueness.

        Args:
            collection_name: The collection name.

        Returns:
            The generated table name.
        """
        # Use lowercase and prefix to distinguish from system tables
        return f"col_{collection_name.lower()}"

    @classmethod
    def build_column_def(cls, field: dict[str, Any], table_name: str) -> tuple[str, str | None]:
        """Build column definition for a single field.

        Args:
            field: The field definition dict.
            table_name: The parent table name (for reference constraints).

        Returns:
            Tuple of (column definition, optional foreign key constraint).
        """
        name = field["name"]
        field_type = field["type"].lower()
        sql_type = FIELD_TYPE_TO_SQL.get(field_type, "TEXT")

        # Build column definition parts
        parts = [f'"{name}"', sql_type]

        # Handle NOT NULL for required fields
        if field.get("required", False):
            parts.append("NOT NULL")

        # Handle default values
        default = field.get("default")
        if default is not None:
            if isinstance(default, str):
                parts.append(f"DEFAULT '{default}'")
            elif isinstance(default, bool):
                parts.append(f"DEFAULT {1 if default else 0}")
            else:
                parts.append(f"DEFAULT {default}")

        # Handle unique constraint
        if field.get("unique", False):
            parts.append("UNIQUE")

        column_def = " ".join(parts)

        # Handle foreign key for reference type
        fk_constraint = None
        if field_type == FieldType.REFERENCE.value:
            target_collection = field.get("collection", "")
            on_delete = field.get("on_delete", OnDeleteAction.RESTRICT.value).upper()

            # Map on_delete values to SQL
            on_delete_map = {
                "CASCADE": "CASCADE",
                "SET_NULL": "SET NULL",
                "RESTRICT": "RESTRICT",
            }
            on_delete_sql = on_delete_map.get(on_delete.replace("_", ""), "RESTRICT")

            # Generate target table name
            target_table = cls.generate_table_name(target_collection)
            fk_constraint = f'FOREIGN KEY ("{name}") REFERENCES "{target_table}"("id") ON DELETE {on_delete_sql}'

        return column_def, fk_constraint

    @classmethod
    def build_create_table_ddl(cls, collection_name: str, schema: list[dict[str, Any]]) -> str:
        """Build complete CREATE TABLE DDL statement.

        Args:
            collection_name: The collection name.
            schema: List of field definitions.

        Returns:
            The DDL statement as a string.
        """
        table_name = cls.generate_table_name(collection_name)

        # Start with system columns
        column_defs = [f'"{col}" {col_type}' for col, col_type in SYSTEM_COLUMNS]

        # Build user field columns
        fk_constraints = []
        for field in schema:
            col_def, fk_constraint = cls.build_column_def(field, table_name)
            column_defs.append(col_def)
            if fk_constraint:
                fk_constraints.append(fk_constraint)

        # Combine columns and constraints
        all_parts = column_defs + fk_constraints
        columns_sql = ",\n  ".join(all_parts)

        ddl = f'CREATE TABLE "{table_name}" (\n  {columns_sql}\n);'
        return ddl

    @classmethod
    def build_index_ddl(cls, collection_name: str, schema: list[dict[str, Any]]) -> list[str]:
        """Build CREATE INDEX statements for the table.

        Creates indexes on:
        - account_id (always, for multi-tenancy queries)
        - Any unique fields

        Args:
            collection_name: The collection name.
            schema: List of field definitions.

        Returns:
            List of DDL statements for indexes.
        """
        table_name = cls.generate_table_name(collection_name)
        indexes = []

        # Always index account_id for multi-tenancy queries
        indexes.append(
            f'CREATE INDEX "idx_{table_name}_account_id" ON "{table_name}"("account_id");'
        )

        # Index unique fields (SQLite may already create these for UNIQUE constraint)
        # Also index reference fields for join performance
        for field in schema:
            name = field["name"]
            field_type = field.get("type", "").lower()

            if field_type == FieldType.REFERENCE.value:
                indexes.append(
                    f'CREATE INDEX "idx_{table_name}_{name}" ON "{table_name}"("{name}");'
                )

        return indexes

    @classmethod
    async def create_table(
        cls, engine: AsyncEngine, collection_name: str, schema: list[dict[str, Any]]
    ) -> None:
        """Create the physical table and indexes.

        Args:
            engine: SQLAlchemy async engine.
            collection_name: The collection name.
            schema: List of field definitions.
        """
        table_name = cls.generate_table_name(collection_name)

        # Build DDL statements
        create_table_ddl = cls.build_create_table_ddl(collection_name, schema)
        index_ddls = cls.build_index_ddl(collection_name, schema)

        logger.info(
            "Creating collection table",
            table_name=table_name,
            collection_name=collection_name,
        )

        async with engine.begin() as conn:
            # Create table
            await conn.execute(text(create_table_ddl))
            logger.debug("Table created", table_name=table_name, ddl=create_table_ddl)

            # Create indexes
            for index_ddl in index_ddls:
                await conn.execute(text(index_ddl))
                logger.debug("Index created", ddl=index_ddl)

        logger.info("Collection table created successfully", table_name=table_name)

    @classmethod
    async def table_exists(cls, engine: AsyncEngine, collection_name: str) -> bool:
        """Check if a table already exists.

        Args:
            engine: SQLAlchemy async engine.
            collection_name: The collection name.

        Returns:
            True if table exists, False otherwise.
        """
        table_name = cls.generate_table_name(collection_name)

        # SQLite-specific query to check table existence
        check_sql = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=:table_name
        """

        async with engine.connect() as conn:
            result = await conn.execute(text(check_sql), {"table_name": table_name})
            return result.scalar_one_or_none() is not None

    @classmethod
    def build_add_column_ddl(
        cls, collection_name: str, fields: list[dict[str, Any]]
    ) -> list[str]:
        """Build ALTER TABLE ADD COLUMN statements for new fields.

        Args:
            collection_name: The collection name.
            fields: List of new field definitions to add.

        Returns:
            List of DDL statements.
        """
        table_name = cls.generate_table_name(collection_name)
        ddl_statements = []

        for field in fields:
            name = field["name"]
            field_type = field["type"].lower()
            sql_type = FIELD_TYPE_TO_SQL.get(field_type, "TEXT")

            # Build column definition parts
            parts = [f'"{name}"', sql_type]

            # Note: SQLite doesn't support adding NOT NULL columns without a default
            # So we only add NOT NULL if there's a default value
            default = field.get("default")
            if default is not None:
                if isinstance(default, str):
                    parts.append(f"DEFAULT '{default}'")
                elif isinstance(default, bool):
                    parts.append(f"DEFAULT {1 if default else 0}")
                else:
                    parts.append(f"DEFAULT {default}")

                # Now we can add NOT NULL if required
                if field.get("required", False):
                    parts.append("NOT NULL")

            column_def = " ".join(parts)
            ddl = f'ALTER TABLE "{table_name}" ADD COLUMN {column_def};'
            ddl_statements.append(ddl)

        return ddl_statements

    @classmethod
    async def add_columns(
        cls, engine: AsyncEngine, collection_name: str, fields: list[dict[str, Any]]
    ) -> None:
        """Execute ALTER TABLE to add new columns.

        Args:
            engine: SQLAlchemy async engine.
            collection_name: The collection name.
            fields: List of new field definitions to add.
        """
        table_name = cls.generate_table_name(collection_name)
        ddl_statements = cls.build_add_column_ddl(collection_name, fields)

        logger.info(
            "Adding columns to collection table",
            table_name=table_name,
            collection_name=collection_name,
            field_count=len(fields),
        )

        async with engine.begin() as conn:
            for ddl in ddl_statements:
                await conn.execute(text(ddl))
                logger.debug("Column added", ddl=ddl)

        logger.info(
            "Columns added successfully",
            table_name=table_name,
            field_count=len(fields),
        )

    @classmethod
    async def drop_table(cls, engine: AsyncEngine, collection_name: str) -> None:
        """Drop a collection table.

        Args:
            engine: SQLAlchemy async engine.
            collection_name: The collection name.
        """
        table_name = cls.generate_table_name(collection_name)

        logger.info(
            "Dropping collection table",
            table_name=table_name,
            collection_name=collection_name,
        )

        async with engine.begin() as conn:
            ddl = f'DROP TABLE IF EXISTS "{table_name}";'
            await conn.execute(text(ddl))
            logger.debug("Table dropped", ddl=ddl)

        logger.info("Collection table dropped successfully", table_name=table_name)

