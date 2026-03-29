"""Repository for dynamic record operations.

Provides CRUD operations for dynamic collection tables using raw SQL,
since tables are created dynamically and not mapped to ORM models.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.context import get_current_context
from snackbase.core.cursor import encode_cursor
from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)


@dataclass
class RuleFilter:
    """Rule results including SQL filter for row-level security."""
    sql: str
    params: dict[str, Any]
    allowed_fields: list[str] | str = "*"


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

    def _get_dialect(self) -> str:
        """Get the database dialect name.

        Returns:
            The dialect name (e.g., 'sqlite', 'postgresql').
        """
        if self.session.bind and hasattr(self.session.bind, 'dialect'):
            return self.session.bind.dialect.name
        return "sqlite"  # Default fallback

    def _convert_boolean_for_db(self, value: bool) -> bool | int:
        """Convert a boolean value for database storage.

        PostgreSQL supports native booleans, SQLite uses 0/1.

        Args:
            value: The boolean value to convert.

        Returns:
            Native bool for PostgreSQL, int (0/1) for SQLite.
        """
        if self._get_dialect() == "postgresql":
            return value
        return 1 if value else 0

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
        now = datetime.now(UTC)

        # Build system fields
        system_fields = {
            "id": record_id,
            "account_id": account_id,
            "created_at": now,
            "created_by": created_by,
            "updated_at": now,
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
                    sql_values[key] = self._convert_boolean_for_db(value)
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
        created_record = {
            "id": record_id,
            "account_id": account_id,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "updated_at": now.isoformat(),
            "updated_by": created_by,
            **data,  # Include original user data (not SQL-converted)
        }

        # Trigger audit hook if context is available
        context = get_current_context()
        if context and hasattr(context, "app") and hasattr(context.app.state, "hook_registry"):
            registry = context.app.state.hook_registry
            await registry.trigger(
                HookEvent.ON_RECORD_AFTER_CREATE,
                {"record": created_record, "collection": collection_name, "session": self.session},
                context
            )

        return created_record

    async def update_record(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        updated_by: str,
        data: dict[str, Any],
        schema: list[dict[str, Any]],
        old_values: dict[str, Any] | None = None,
        rule_filter: RuleFilter | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing record.

        Args:
            collection_name: The collection name.
            record_id: The record ID.
            account_id: The account ID for scoping.
            updated_by: The user ID performing the update.
            data: The fields to update.
            schema: The collection schema.
            old_values: Optional old values for audit logging.
            rule_filter: Optional rule filter for row-level security.

        Returns:
            The updated record dict, or None if not found/access denied.
        """
        table_name = TableBuilder.generate_table_name(collection_name)
        now = datetime.now(UTC)

        # 1. Prepare update values
        schema_lookup = {f["name"]: f for f in schema}
        sql_values = {}

        for key, value in data.items():
            if key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    sql_values[key] = json.dumps(value)
                elif field_type == "boolean":
                    if isinstance(value, bool):
                        sql_values[key] = self._convert_boolean_for_db(value)
                    else:
                        sql_values[key] = value
                else:
                    sql_values[key] = value

        # Always update system fields
        sql_values["updated_at"] = now
        sql_values["updated_by"] = updated_by

        # 2. Build UPDATE statement
        set_clauses = [f'"{k}" = :{k}' for k in sql_values.keys()]
        set_clause = ", ".join(set_clauses)

        # Build WHERE clause
        where_clauses = ['"id" = :record_id']
        params = {**sql_values, "record_id": record_id}

        if account_id:
            where_clauses.append('"account_id" = :account_id')
            params["account_id"] = account_id

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        where_clause = " AND ".join(where_clauses)

        update_sql = f'''
            UPDATE "{table_name}"
            SET {set_clause}
            WHERE {where_clause}
            RETURNING *
        '''

        # 3. Execute
        result = await self.session.execute(text(update_sql), params)
        row = result.fetchone()

        if row is None:
            return None

        # Convert back to dict
        record = dict(row._mapping)

        # Type conversion
        for key, value in list(record.items()):
            # System fields: convert datetime to ISO string
            if key in ("created_at", "updated_at") and isinstance(value, datetime):
                record[key] = value.isoformat()
            elif key in schema_lookup:
                field_type = schema_lookup[key].get("type", "text").lower()
                if field_type == "json" and value is not None:
                    try:
                        record[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif field_type == "boolean":
                    record[key] = bool(value)

        # Trigger audit hook for update
        context = get_current_context()
        if context and hasattr(context, "app") and hasattr(context.app.state, "hook_registry"):
            registry = context.app.state.hook_registry
            # For updates, we pass the new record and optionally old_values.
            # RecordRepository doesn't keep track of old_values easily,
            # but AuditLogService will compare.
            # Wait, AuditLogService needs old_values to compare!
            # If we don't pass them, it won't see changes.
            # But the 'data' passed to update_record ARE the changes.

            # TODO: If we want full audit, we might need to pass old_values here too.
            # Let's see if we can get them from the RETURNING row?
            # SQLite RETURNING only returns NEW values.

            await registry.trigger(
                HookEvent.ON_RECORD_AFTER_UPDATE,
                {
                    "record": record,
                    "collection": collection_name,
                    "data": data,
                    "old_values": old_values,
                    "session": self.session,
                },
                context
            )

        return record

    async def get_by_id(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        schema: list[dict[str, Any]],
        rule_filter: RuleFilter | None = None,
    ) -> dict[str, Any] | None:
        """Get a record by ID, scoped to account and rules.

        Args:
            collection_name: The collection name.
            record_id: The record ID.
            account_id: The account ID for scoping.
            schema: The collection schema for type conversion.
            rule_filter: Optional rule filter for row-level security.

        Returns:
            The record dict if found, None otherwise.
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        # Build WHERE clause
        where_clauses = ['"id" = :record_id']
        params = {"record_id": record_id}

        if account_id:
            where_clauses.append('"account_id" = :account_id')
            params["account_id"] = account_id

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        where_clause = " AND ".join(where_clauses)

        select_sql = f'''
            SELECT * FROM "{table_name}"
            WHERE {where_clause}
        '''

        result = await self.session.execute(
            text(select_sql),
            params,
        )

        row = result.fetchone()
        if row is None:
            return None

        # Convert row to dict
        record = dict(row._mapping)

        # Convert types back from SQL storage
        schema_lookup = {f["name"]: f for f in schema}
        for key, value in list(record.items()):
            # System fields: convert datetime to ISO string
            if key in ("created_at", "updated_at") and isinstance(value, datetime):
                record[key] = value.isoformat()
            elif key in schema_lookup:
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

        # Check if record exists with account scoping
        # Note: If the table doesn't exist, this query will fail with a database error,
        # which is appropriate since it indicates a configuration issue (missing collection).
        check_sql = f'''
            SELECT 1 FROM "{table_name}"
            WHERE "id" = :reference_id AND "account_id" = :account_id
            LIMIT 1
        '''

        try:
            result = await self.session.execute(
                text(check_sql),
                {"reference_id": reference_id, "account_id": account_id},
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            # Table doesn't exist or query failed - reference is invalid
            return False

    async def get_by_ids(
        self,
        collection_name: str,
        ids: list[str],
        account_id: str | None,
        schema: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Batch-fetch records by a list of IDs, scoped to account.

        Args:
            collection_name: The collection name.
            ids: List of record IDs to fetch.
            account_id: The account ID for scoping (None for superadmin bypass).
            schema: The collection schema for type conversion.

        Returns:
            Dict mapping record ID to record dict for found records.
        """
        if not ids:
            return {}

        table_name = TableBuilder.generate_table_name(collection_name)
        id_params = {f"id_{i}": v for i, v in enumerate(ids)}
        placeholders = ", ".join(f":{k}" for k in id_params)
        where_clauses = [f'"id" IN ({placeholders})']
        params: dict[str, Any] = {**id_params}

        if account_id:
            where_clauses.append('"account_id" = :account_id')
            params["account_id"] = account_id

        where_clause = " AND ".join(where_clauses)
        select_sql = f'SELECT * FROM "{table_name}" WHERE {where_clause}'

        try:
            result = await self.session.execute(text(select_sql), params)
            rows = result.fetchall()
        except Exception:
            return {}

        schema_lookup = {f["name"]: f for f in schema}
        records: dict[str, dict[str, Any]] = {}

        for row in rows:
            record = dict(row._mapping)
            for key, value in list(record.items()):
                if key in ("created_at", "updated_at") and isinstance(value, datetime):
                    record[key] = value.isoformat()
                elif key in schema_lookup:
                    field_type = schema_lookup[key].get("type", "text").lower()
                    if field_type == "json" and value is not None:
                        try:
                            record[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif field_type == "boolean":
                        record[key] = bool(value)
            records[record["id"]] = record

        return records

    async def find_all(
        self,
        collection_name: str,
        account_id: str,
        schema: list[dict[str, Any]],
        skip: int = 0,
        limit: int = 30,
        sort_by: str = "created_at",
        descending: bool = True,
        user_filter: RuleFilter | None = None,
        rule_filter: RuleFilter | None = None,
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
            user_filter: Optional compiled filter from ?filter= query param.
            rule_filter: Optional rule filter for row-level security.

        Returns:
            A tuple containing (list of records, total count).
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        # 1. Build base query components
        where_clauses = []
        params: dict[str, Any] = {}

        # Superadmin bypass check (account_id=None)
        if account_id:
            where_clauses.append('r."account_id" = :account_id')
            params["account_id"] = account_id

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        if user_filter:
            where_clauses.append(f"({user_filter.sql})")
            params.update(user_filter.params)

        # Validate sort field to prevent SQL injection
        # Allow system fields and schema fields
        schema_field_names = {f["name"] for f in schema}
        system_fields = {"id", "created_at", "created_by", "updated_at", "updated_by"}

        if sort_by not in schema_field_names and sort_by not in system_fields:
            # Fallback to default if invalid sort field
            sort_by = "created_at"

        where_clause = " AND ".join(where_clauses)
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        # 2. Get total count
        count_sql = f'SELECT COUNT(*) FROM "{table_name}" r {where_sql}'
        count_result = await self.session.execute(text(count_sql), params)
        total_count = count_result.scalar_one()

        # 3. Get paginated records
        sort_order = "DESC" if descending else "ASC"

        select_sql = f'''
            SELECT r.*, a.name as account_name FROM "{table_name}" r
            LEFT JOIN accounts a ON r.account_id = a.id
            {where_sql}
            ORDER BY r."{sort_by}" {sort_order}
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
                # System fields: convert datetime to ISO string
                if key in ("created_at", "updated_at") and isinstance(value, datetime):
                    record[key] = value.isoformat()
                elif key in schema_lookup:
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

    async def find_all_cursor(
        self,
        collection_name: str,
        account_id: str | None,
        schema: list[dict[str, Any]],
        limit: int = 30,
        sort_by: str = "created_at",
        descending: bool = True,
        user_filter: RuleFilter | None = None,
        rule_filter: RuleFilter | None = None,
        cursor_sort_value: Any = None,
        cursor_record_id: str | None = None,
        is_backward: bool = False,
        include_count: bool = False,
    ) -> tuple[list[dict[str, Any]], str | None, str | None, bool, int | None]:
        """Find records using cursor-based pagination.

        Args:
            collection_name: The collection name.
            account_id: The account ID for scoping (None for superadmin bypass).
            schema: The collection schema for type conversion.
            limit: Maximum number of records to return.
            sort_by: Field to sort by.
            descending: Whether to sort in descending order.
            user_filter: Optional compiled filter from ?filter= query param.
            rule_filter: Optional rule filter for row-level security.
            cursor_sort_value: Sort value from cursor (for keyset pagination).
            cursor_record_id: Record ID from cursor (tie-breaker).
            is_backward: Whether this is a backward navigation request.
            include_count: Whether to include total count (expensive).

        Returns:
            A tuple containing (records, next_cursor, prev_cursor, has_more, total).
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        # 1. Build base query components
        where_clauses = []
        params: dict[str, Any] = {}

        # Account scoping
        if account_id:
            where_clauses.append('r."account_id" = :account_id')
            params["account_id"] = account_id

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        if user_filter:
            where_clauses.append(f"({user_filter.sql})")
            params.update(user_filter.params)

        # Validate sort field
        schema_field_names = {f["name"] for f in schema}
        system_fields = {"id", "created_at", "created_by", "updated_at", "updated_by"}
        if sort_by not in schema_field_names and sort_by not in system_fields:
            sort_by = "created_at"

        # 2. Build cursor condition for keyset pagination
        cursor_condition = ""
        if cursor_sort_value is not None and cursor_record_id is not None:
            sort_order = "DESC" if descending else "ASC"
            opposite_order = "ASC" if descending else "DESC"

            if is_backward:
                # For backward navigation, we want records BEFORE the cursor
                # Since we're sorting DESC, "before" means higher values
                if descending:
                    cursor_condition = f'AND ((r."{sort_by}" > :cursor_sort_value) OR (r."{sort_by}" = :cursor_sort_value AND r."id" > :cursor_record_id))'
                else:
                    cursor_condition = f'AND ((r."{sort_by}" < :cursor_sort_value) OR (r."{sort_by}" = :cursor_sort_value AND r."id" < :cursor_record_id))'
            else:
                # For forward navigation, we want records AFTER the cursor
                if descending:
                    cursor_condition = f'AND ((r."{sort_by}" < :cursor_sort_value) OR (r."{sort_by}" = :cursor_sort_value AND r."id" < :cursor_record_id))'
                else:
                    cursor_condition = f'AND ((r."{sort_by}" > :cursor_sort_value) OR (r."{sort_by}" = :cursor_sort_value AND r."id" > :cursor_record_id))'

            params["cursor_sort_value"] = cursor_sort_value
            params["cursor_record_id"] = cursor_record_id

        where_clause = " AND ".join(where_clauses)
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        # 3. Get total count if requested (expensive)
        total_count = None
        if include_count:
            count_sql = f'SELECT COUNT(*) FROM "{table_name}" r {where_sql}'
            count_result = await self.session.execute(text(count_sql), params)
            total_count = count_result.scalar_one()

        # 4. Get records with cursor pagination
        sort_order = "DESC" if descending else "ASC"

        select_sql = f'''
            SELECT r.*, a.name as account_name FROM "{table_name}" r
            LEFT JOIN accounts a ON r.account_id = a.id
            {where_sql} {cursor_condition}
            ORDER BY r."{sort_by}" {sort_order}, r."id" {sort_order}
            LIMIT :limit
        '''

        params["limit"] = limit + 1  # Get one extra to determine has_more

        result = await self.session.execute(text(select_sql), params)
        rows = result.fetchall()

        # 5. Process results
        records = []
        schema_lookup = {f["name"]: f for f in schema}

        has_more = len(rows) > limit
        actual_rows = rows[:limit]  # Trim to requested limit

        for row in actual_rows:
            record = dict(row._mapping)

            # Type conversion
            for key, value in list(record.items()):
                if key in ("created_at", "updated_at") and isinstance(value, datetime):
                    record[key] = value.isoformat()
                elif key in schema_lookup:
                    field_type = schema_lookup[key].get("type", "text").lower()
                    if field_type == "json" and value is not None:
                        try:
                            record[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif field_type == "boolean":
                        record[key] = bool(value)

            records.append(record)

        # 6. Generate cursors
        next_cursor = None
        prev_cursor = None

        if records:
            # Next cursor: from the last record
            last_record = records[-1]
            next_cursor = encode_cursor(last_record[sort_by], last_record["id"])

            # Prev cursor: from the first record (for backward navigation)
            first_record = records[0]
            prev_cursor = encode_cursor(first_record[sort_by], first_record["id"])

        return records, next_cursor, prev_cursor, has_more, total_count

    async def aggregate_records(
        self,
        collection_name: str,
        account_id: str | None,
        agg_functions: list[Any],
        group_by_fields: list[str],
        user_filter: "RuleFilter | None" = None,
        rule_filter: "RuleFilter | None" = None,
        having_sql: str | None = None,
        having_params: dict[str, Any] | None = None,
        schema: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Run a database-level aggregation query against a collection.

        Args:
            collection_name: The collection name.
            account_id: The account ID for scoping (None for superadmin bypass).
            agg_functions: Validated AggFunction instances from aggregation_parser.
            group_by_fields: Validated field names to group by.
            user_filter: Optional compiled filter from ?filter= query param.
            rule_filter: Optional rule filter for row-level security.
            having_sql: Optional HAVING SQL fragment (already substituted with sql_expr).
            having_params: Optional params for the HAVING clause (hp_ prefix).
            schema: Optional collection schema for type conversion of group-by fields.

        Returns:
            A tuple of (result_rows, total_groups).
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        # 1. Build SELECT clause
        select_parts: list[str] = []
        for agg in agg_functions:
            select_parts.append(f'{agg.sql_expr} AS "{agg.alias}"')
        for field in group_by_fields:
            select_parts.append(f'r."{field}"')
        select_clause = ", ".join(select_parts)

        # 2. Build WHERE clause (same pattern as find_all)
        where_clauses: list[str] = []
        params: dict[str, Any] = {}

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        if user_filter:
            where_clauses.append(f"({user_filter.sql})")
            params.update(user_filter.params)

        # Set account_id after other params to prevent overwrite
        if account_id:
            where_clauses.append('r."account_id" = :account_id')
            params["account_id"] = account_id

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # 3. Build GROUP BY clause
        group_by_sql = ""
        if group_by_fields:
            group_by_parts = [f'r."{f}"' for f in group_by_fields]
            group_by_sql = f"GROUP BY {', '.join(group_by_parts)}"

        # 4. Build HAVING clause
        having_sql_clause = ""
        if having_sql:
            having_sql_clause = f"HAVING {having_sql}"
            if having_params:
                params.update(having_params)

        # 5. Execute main query
        query_sql = f"""
            SELECT {select_clause}
            FROM "{table_name}" r
            {where_sql}
            {group_by_sql}
            {having_sql_clause}
        """
        result = await self.session.execute(text(query_sql), params)
        rows = result.fetchall()

        # 6. Determine total_groups
        if group_by_fields:
            count_sql = f"""
                SELECT COUNT(*) FROM (
                    SELECT 1
                    FROM "{table_name}" r
                    {where_sql}
                    {group_by_sql}
                    {having_sql_clause}
                ) _agg_count
            """
            count_result = await self.session.execute(text(count_sql), params)
            total_groups = count_result.scalar_one()
        else:
            # Global aggregate always produces at most one row
            total_groups = len(rows)

        # 7. Convert rows to dicts with optional type conversion for group-by datetime fields
        schema_lookup = {f["name"]: f for f in (schema or [])}
        results: list[dict[str, Any]] = []
        for row in rows:
            row_dict = dict(row._mapping)
            for field in group_by_fields:
                val = row_dict.get(field)
                if val is None:
                    continue
                field_def = schema_lookup.get(field)
                if field_def:
                    field_type = field_def.get("type", "text").lower()
                    if field_type in ("date", "datetime") and isinstance(val, datetime):
                        row_dict[field] = val.isoformat()
            results.append(row_dict)

        return results, total_groups

    async def delete_record(
        self,
        collection_name: str,
        record_id: str,
        account_id: str,
        record_data: dict[str, Any] | None = None,
        rule_filter: RuleFilter | None = None,
    ) -> bool:
        """Delete a record by ID, scoped to account and rules.

        Args:
            collection_name: The collection name.
            record_id: The record ID.
            account_id: The account ID for scoping.
            record_data: Optional existing record data for hook.
            rule_filter: Optional rule filter for row-level security.

        Returns:
            True if record was deleted, False if not found.
        """
        table_name = TableBuilder.generate_table_name(collection_name)

        # Build WHERE clause
        where_clauses = ['"id" = :record_id']
        params = {"record_id": record_id}

        if account_id:
            where_clauses.append('"account_id" = :account_id')
            params["account_id"] = account_id

        if rule_filter:
            where_clauses.append(f"({rule_filter.sql})")
            params.update(rule_filter.params)

        where_clause = " AND ".join(where_clauses)

        delete_sql = f'''
            DELETE FROM "{table_name}"
            WHERE {where_clause}
        '''

        result = await self.session.execute(
            text(delete_sql),
            params,
        )

        success = result.rowcount > 0

        if success and record_data:
            # Trigger audit hook if context is available
            context = get_current_context()
            if context and hasattr(context, "app") and hasattr(context.app.state, "hook_registry"):
                registry = context.app.state.hook_registry
                await registry.trigger(
                    HookEvent.ON_RECORD_AFTER_DELETE,
                    {"record": record_data, "collection": collection_name, "session": self.session},
                    context
                )

        return success

    async def batch_insert_records(
        self,
        collection_name: str,
        account_id: str,
        created_by: str,
        records_data: list[dict[str, Any]],
        schema: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Insert multiple records within a single transaction.

        Each record is inserted via the existing insert_record() method so that
        hooks, audit events, and type handling are reused per record.
        The caller is responsible for committing or rolling back the transaction.

        Args:
            collection_name: The collection name.
            account_id: The account ID for scoping.
            created_by: The user ID who is creating the records.
            records_data: List of validated record data dicts.
            schema: The collection schema for type handling.

        Returns:
            List of created record dicts in insertion order.

        Raises:
            ValueError: With message "index={i}" on failure, so the caller can roll back.
        """
        import uuid as _uuid
        created = []
        for i, data in enumerate(records_data):
            try:
                record = await self.insert_record(
                    collection_name=collection_name,
                    record_id=str(_uuid.uuid4()),
                    account_id=account_id,
                    created_by=created_by,
                    data=data,
                    schema=schema,
                )
                created.append(record)
            except Exception as exc:
                raise ValueError(f"index={i}") from exc
        return created

    async def batch_update_records(
        self,
        collection_name: str,
        account_id: str | None,
        updated_by: str,
        updates: list[dict[str, Any]],
        schema: list[dict[str, Any]],
        rule_filter: RuleFilter | None = None,
    ) -> list[dict[str, Any]]:
        """Patch multiple records within a single transaction.

        Each update dict must have keys: "id", "data", and optionally "old_values".
        The caller is responsible for committing or rolling back the transaction.

        Returns:
            List of updated record dicts in request order.

        Raises:
            ValueError: With message "index={i}:not_found" if any record is not found.
        """
        updated = []
        for i, item in enumerate(updates):
            record = await self.update_record(
                collection_name=collection_name,
                record_id=item["id"],
                account_id=account_id,
                updated_by=updated_by,
                data=item["data"],
                schema=schema,
                old_values=item.get("old_values"),
                rule_filter=rule_filter,
            )
            if record is None:
                raise ValueError(f"index={i}:not_found")
            updated.append(record)
        return updated

    async def batch_delete_records(
        self,
        collection_name: str,
        account_id: str | None,
        record_ids: list[str],
        records_data: dict[str, dict[str, Any]],
        rule_filter: RuleFilter | None = None,
    ) -> list[str]:
        """Delete multiple records within a single transaction.

        The caller is responsible for committing or rolling back the transaction.

        Args:
            collection_name: The collection name.
            account_id: The account ID for scoping (None for superadmin bypass).
            record_ids: List of record IDs to delete.
            records_data: Mapping of record_id → record dict for hook/audit data.
            rule_filter: Optional rule filter for row-level security.

        Returns:
            List of deleted record IDs.

        Raises:
            ValueError: With message "index={i}:not_found:{rid}" if any record is not found.
        """
        deleted_ids = []
        for i, record_id in enumerate(record_ids):
            success = await self.delete_record(
                collection_name=collection_name,
                record_id=record_id,
                account_id=account_id,
                record_data=records_data.get(record_id),
                rule_filter=rule_filter,
            )
            if not success:
                raise ValueError(f"index={i}:not_found:{record_id}")
            deleted_ids.append(record_id)
        return deleted_ids
