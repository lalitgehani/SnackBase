"""Repository for dynamic record operations.

Provides CRUD operations for dynamic collection tables using raw SQL,
since tables are created dynamically and not mapped to ORM models.
"""

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


class RecordRepository:
    """Repository for dynamic record database operations.

    Uses raw SQL since collection tables are dynamically created
    and not mapped to SQLAlchemy ORM models.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def insert_record(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        created_by: str,
        data: dict[str, Any],
        schema: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Insert a new record into a collection table.

        Args:
            collection_name: The collection name.
            record_id: The generated record ID.
            account_id: The account ID from the user's token.
            created_by: The user ID who created the record.
            data: The validated record data (user fields only).
            schema: The collection schema for type handling.

        Returns:
            The complete record dict including system fields.
        """
        table_name = TableBuilder.generate_table_name(collection_name)
        now = datetime.utcnow()

        # Build system fields
        system_fields = {
            "id": record_id,
            "account_id": account_id,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "updated_at": now.isoformat(),
            "updated_by": created_by,
        }

        # Merge with user data
        all_data = {**system_fields, **data}

        # Prepare values for SQL - handle JSON fields
        schema_lookup = {f["name"]: f for f in schema}
        sql_values = {}
        for key, value in all_data.items():
            if key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    sql_values[key] = json.dumps(value)
                elif field_type == "boolean" and isinstance(value, bool):
                    sql_values[key] = 1 if value else 0
                else:
                    sql_values[key] = value
            else:
                # System field
                sql_values[key] = value

        # Build INSERT statement
        columns = ", ".join(f'"{k}"' for k in sql_values.keys())
        placeholders = ", ".join(f":{k}" for k in sql_values.keys())

        insert_sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'

        logger.debug(
            "Inserting record",
            table_name=table_name,
            record_id=record_id,
            account_id=account_id,
        )

        await self.session.execute(text(insert_sql), sql_values)

        logger.info(
            "Record inserted successfully",
            table_name=table_name,
            record_id=record_id,
            account_id=account_id,
            created_by=created_by,
        )


        # Return the complete record
        return {
            "id": record_id,
            "account_id": account_id,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "updated_at": now.isoformat(),
            "updated_by": created_by,
            **data,  # Include original user data (not SQL-converted)
        }

    async def update_record(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        updated_by: str,
        data: dict[str, Any],
        schema: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Update an existing record.
        
        Args:
            collection_name: The collection name.
            record_id: The record ID.
            account_id: The account ID for scoping.
            updated_by: The user ID performing the update.
            data: The fields to update.
            schema: The collection schema.
            
        Returns:
            The updated record dict, or None if not found/access denied.
        """
        table_name = TableBuilder.generate_table_name(collection_name)
        now = datetime.utcnow()
        
        # 1. Prepare update values
        schema_lookup = {f["name"]: f for f in schema}
        sql_values = {}
        
        for key, value in data.items():
            if key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    sql_values[key] = json.dumps(value)
                elif field_type == "boolean":
                    # Handle boolean explicitly
                    if isinstance(value, bool):
                        sql_values[key] = 1 if value else 0
                    else:
                        sql_values[key] = value # let SQL handle it or it might be already int
                else:
                    sql_values[key] = value
                    
        # Always update system fields
        sql_values["updated_at"] = now.isoformat()
        sql_values["updated_by"] = updated_by
        
        # 2. Build UPDATE statement
        set_clauses = [f'"{k}" = :{k}' for k in sql_values.keys()]
        set_clause = ", ".join(set_clauses)
        
        update_sql = f'''
            UPDATE "{table_name}"
            SET {set_clause}
            WHERE "id" = :record_id AND "account_id" = :account_id
            RETURNING *
        '''
        
        # Add WHERE params
        params = {**sql_values, "record_id": record_id, "account_id": account_id}
        
        # 3. Execute
        result = await self.session.execute(text(update_sql), params)
        row = result.fetchone()
        
        if row is None:
            return None
            
        # 4. Convert back to dict
        record = dict(row._mapping)
        
        # Type conversion
        for key, value in list(record.items()):
            if key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    try:
                        record[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif field_type == "boolean":
                    record[key] = bool(value)
                    
        return record

    async def get_by_id(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        schema: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Get a record by ID, scoped to account.

        Args:
            collection_name: The collection name.
            record_id: The record ID.
            account_id: The account ID for scoping.
            schema: The collection schema for type conversion.

        Returns:
            The record dict if found, None otherwise.
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        select_sql = f'''
            SELECT * FROM "{table_name}"
            WHERE "id" = :record_id AND "account_id" = :account_id
        '''

        result = await self.session.execute(
            text(select_sql),
            {"record_id": record_id, "account_id": account_id},
        )

        row = result.fetchone()
        if row is None:
            return None

        # Convert row to dict
        record = dict(row._mapping)

        # Convert types back from SQL storage
        schema_lookup = {f["name"]: f for f in schema}
        for key, value in list(record.items()):
            if key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    try:
                        record[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Keep original value
                elif field_type == "boolean":
                    record[key] = bool(value)

        return record

    async def check_reference_exists(
        self,
        target_collection: str,
        reference_id: str,
        account_id: str,
    ) -> bool:
        """Check if a referenced record exists and belongs to the same account.

        Args:
            target_collection: The target collection name.
            reference_id: The ID of the referenced record.
            account_id: The account ID for scoping.

        Returns:
            True if reference exists and is accessible, False otherwise.
        """
        table_name = TableBuilder.generate_table_name(target_collection)

        # First check if table exists
        check_table_sql = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=:table_name
        """
        table_result = await self.session.execute(
            text(check_table_sql), {"table_name": table_name}
        )
        if table_result.scalar_one_or_none() is None:
            return False

        # Check if record exists with account scoping
        check_sql = f'''
            SELECT 1 FROM "{table_name}"
            WHERE "id" = :reference_id AND "account_id" = :account_id
            LIMIT 1
        '''

        result = await self.session.execute(
            text(check_sql),
            {"reference_id": reference_id, "account_id": account_id},
        )

        return result.scalar_one_or_none() is not None

    async def find_all(
        self,
        collection_name: str,
        account_id: str,
        schema: list[dict[str, Any]],
        skip: int = 0,
        limit: int = 30,
        sort_by: str = "created_at",
        descending: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Find records in a collection with pagination, sorting, and filtering.

        Args:
            collection_name: The collection name.
            account_id: The account ID for scoping.
            schema: The collection schema for type conversion.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            sort_by: Field to sort by.
            descending: Whether to sort in descending order.
            filters: Optional dictionary of filter conditions (field=value).

        Returns:
            A tuple containing (list of records, total count).
        """
        table_name = TableBuilder.generate_table_name(collection_name)
        filters = filters or {}

        # 1. Build base query components
        where_clauses = ['"account_id" = :account_id']
        params = {"account_id": account_id}

        # Validate sort field to prevent SQL injection
        # Allow system fields and schema fields
        schema_field_names = {f["name"] for f in schema}
        system_fields = {"id", "created_at", "created_by", "updated_at", "updated_by"}
        
        if sort_by not in schema_field_names and sort_by not in system_fields:
            # Fallback to default if invalid sort field
            sort_by = "created_at"

        # Apply filters
        for field, value in filters.items():
            if field in schema_field_names or field in system_fields:
                param_name = f"filter_{field}"
                where_clauses.append(f'"{field}" = :{param_name}')
                
                # specific handling for boolean or json
                 # Check schema type if it's a schema field
                schema_field = next((f for f in schema if f["name"] == field), None)
                if schema_field:
                    field_type = schema_field.get("type", "text").lower()
                    if field_type == "boolean":
                        if isinstance(value, str):
                            params[param_name] = 1 if value.lower() == "true" else 0
                        else:
                             params[param_name] = 1 if value else 0
                    else:
                        params[param_name] = value
                else:
                    params[param_name] = value

        where_clause = " AND ".join(where_clauses)

        # 2. Get total count
        count_sql = f'SELECT COUNT(*) FROM "{table_name}" WHERE {where_clause}'
        count_result = await self.session.execute(text(count_sql), params)
        total_count = count_result.scalar_one()

        # 3. Get paginated records
        sort_order = "DESC" if descending else "ASC"
        
        select_sql = f'''
            SELECT * FROM "{table_name}"
            WHERE {where_clause}
            ORDER BY "{sort_by}" {sort_order}
            LIMIT :limit OFFSET :skip
        '''
        
        params["limit"] = limit
        params["skip"] = skip

        result = await self.session.execute(text(select_sql), params)
        rows = result.fetchall()

        # 4. Convert rows to dicts and fix types
        records = []
        schema_lookup = {f["name"]: f for f in schema}

        for row in rows:
            record = dict(row._mapping)
            
            # Type conversion (same as get_by_id)
            for key, value in list(record.items()):
                if key in schema_lookup:
                    field_type = schema_lookup[key].get("type", "text").lower()
                    if field_type == "json" and value is not None:
                        try:
                            record[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif field_type == "boolean":
                        record[key] = bool(value)
            
            records.append(record)

        return records, total_count
