"""Validator for SQL queries used in view collections.

Validates that view queries are safe SELECT statements referencing only
base collection tables, and translates friendly collection names to
physical table names.
"""

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder

logger = get_logger(__name__)

# Patterns that indicate dangerous SQL constructs
_DANGEROUS_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE"
    r"|COPY|pg_sleep|lo_import|lo_export|set_config|pg_read_file|pg_write_file"
    r"|pg_terminate_backend|pg_cancel_backend|dblink)\b",
    re.IGNORECASE,
)

# Pattern to match SQL comments
_SQL_COMMENTS = re.compile(
    r"--[^\n]*|/\*.*?\*/",
    re.DOTALL,
)

# Pattern to extract table names from FROM and JOIN clauses
# Matches: FROM <name>, JOIN <name>, from <name> AS <alias>, etc.
_TABLE_REF_PATTERN = re.compile(
    r"""(?:FROM|JOIN)\s+        # FROM or JOIN keyword
    (?:ONLY\s+)?                # optional ONLY keyword
    "?(\w+)"?                   # table name (with optional quotes)
    (?:\s+(?:AS\s+)?\w+)?       # optional alias
    """,
    re.IGNORECASE | re.VERBOSE,
)

# System/internal tables that must never be referenced
_SYSTEM_TABLE_PREFIXES = (
    "pg_",
    "information_schema",
    "sqlite_",
)

_SYSTEM_TABLES = {
    "accounts",
    "users",
    "roles",
    "permissions",
    "collections",
    "collection_rules",
    "configurations",
    "api_keys",
    "audit_logs",
    "groups",
    "users_groups",
    "macros",
    "alembic_version",
    "token_blacklist",
    "email_templates",
    "email_logs",
    "invitations",
    "oauth_states",
    "webhooks",
    "webhook_deliveries",
    "jobs",
    "hooks",
    "hook_executions",
    "endpoints",
    "endpoint_logs",
    "workflows",
    "workflow_instances",
    "workflow_step_logs",
}


@dataclass
class ViewQueryValidationError:
    """A single validation error found in a view query."""

    message: str
    code: str


class ViewQueryValidator:
    """Validates SQL queries for view collections."""

    @classmethod
    def strip_comments(cls, query: str) -> str:
        """Remove SQL comments from the query."""
        return _SQL_COMMENTS.sub(" ", query)

    @classmethod
    def extract_collection_names(cls, query: str) -> list[str]:
        """Extract referenced table/collection names from a SQL query.

        Returns the raw names as they appear in FROM/JOIN clauses.
        """
        cleaned = cls.strip_comments(query)
        matches = _TABLE_REF_PATTERN.findall(cleaned)
        # Deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for name in matches:
            lower = name.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(name)
        return result

    @classmethod
    def translate_table_names(cls, query: str, name_map: dict[str, str]) -> str:
        """Replace friendly collection names with physical table names.

        Args:
            query: The SQL query with friendly names.
            name_map: Mapping of lowercase collection name -> physical table name.

        Returns:
            Query with physical table names.
        """
        cleaned = cls.strip_comments(query)

        def _replace(match: re.Match) -> str:
            full = match.group(0)
            table_name = match.group(1).lower()
            if table_name in name_map:
                physical = name_map[table_name]
                return full.replace(match.group(1), f'"{physical}"')
            return full

        return _TABLE_REF_PATTERN.sub(_replace, cleaned)

    @classmethod
    async def validate(
        cls,
        query: str,
        session: AsyncSession,
    ) -> tuple[list[ViewQueryValidationError], str]:
        """Validate a view SQL query and translate collection names.

        Args:
            query: The SQL query using friendly collection names.
            session: Database session for validating collection existence.

        Returns:
            Tuple of (list of validation errors, translated query).
            If errors is non-empty, the translated query should not be used.
        """
        errors: list[ViewQueryValidationError] = []

        if not query or not query.strip():
            errors.append(
                ViewQueryValidationError(
                    message="View query cannot be empty",
                    code="empty_query",
                )
            )
            return errors, ""

        # 1. Strip comments
        cleaned = cls.strip_comments(query.strip())

        # 2. Check for multiple statements (semicolons)
        # Allow trailing semicolon but reject multiple statements
        parts = [p.strip() for p in cleaned.split(";") if p.strip()]
        if len(parts) > 1:
            errors.append(
                ViewQueryValidationError(
                    message="View query must contain a single SQL statement",
                    code="multiple_statements",
                )
            )
            return errors, ""

        cleaned = parts[0] if parts else cleaned

        # 3. Must start with SELECT (or WITH for CTEs)
        first_word = cleaned.split()[0].upper() if cleaned.split() else ""
        if first_word not in ("SELECT", "WITH"):
            errors.append(
                ViewQueryValidationError(
                    message="View query must be a SELECT statement (optionally using WITH/CTE)",
                    code="not_select",
                )
            )
            return errors, ""

        # 4. Check for dangerous keywords
        dangerous_match = _DANGEROUS_KEYWORDS.search(cleaned)
        if dangerous_match:
            errors.append(
                ViewQueryValidationError(
                    message=f"View query contains a forbidden keyword: {dangerous_match.group(0).upper()}",
                    code="dangerous_keyword",
                )
            )
            return errors, ""

        # 5. Extract referenced table names
        referenced_names = cls.extract_collection_names(cleaned)

        if not referenced_names:
            errors.append(
                ViewQueryValidationError(
                    message="View query must reference at least one collection",
                    code="no_tables",
                )
            )
            return errors, ""

        # 6. Check for system table references
        for name in referenced_names:
            lower_name = name.lower()
            if any(lower_name.startswith(prefix) for prefix in _SYSTEM_TABLE_PREFIXES):
                errors.append(
                    ViewQueryValidationError(
                        message=f"View query cannot reference system table: {name}",
                        code="system_table_reference",
                    )
                )
            if lower_name in _SYSTEM_TABLES:
                errors.append(
                    ViewQueryValidationError(
                        message=f"View query cannot reference system table: {name}",
                        code="system_table_reference",
                    )
                )

        if errors:
            return errors, ""

        # 7. Validate each referenced collection exists and is a base collection
        from snackbase.infrastructure.persistence.repositories import CollectionRepository

        collection_repo = CollectionRepository(session)
        name_map: dict[str, str] = {}

        for ref_name in referenced_names:
            lower_name = ref_name.lower()
            collection = await collection_repo.get_by_name(lower_name)
            if collection is None:
                errors.append(
                    ViewQueryValidationError(
                        message=f"Referenced collection '{ref_name}' does not exist",
                        code="collection_not_found",
                    )
                )
            else:
                coll_type = getattr(collection, "type", "base")
                if coll_type == "view":
                    errors.append(
                        ViewQueryValidationError(
                            message=f"View collections can only reference base collections, not other views. '{ref_name}' is a view collection.",
                            code="view_references_view",
                        )
                    )
                else:
                    name_map[lower_name] = TableBuilder.generate_table_name(lower_name)

        if errors:
            return errors, ""

        # 8. Translate friendly names to physical names
        translated = cls.translate_table_names(cleaned, name_map)

        # 9. Test-execute the translated query to validate SQL syntax
        #    and check for required columns
        try:
            test_sql = f"SELECT * FROM ({translated}) _view_test LIMIT 0"
            result = await session.execute(text(test_sql))
            columns = list(result.keys())

            if "account_id" not in columns:
                errors.append(
                    ViewQueryValidationError(
                        message="View query must include 'account_id' in its output columns for multi-tenant isolation",
                        code="missing_account_id",
                    )
                )

            if "id" not in columns:
                logger.warning(
                    "View query does not include 'id' column - single-record access will not work",
                    query=query[:200],
                )

        except Exception as e:
            errors.append(
                ViewQueryValidationError(
                    message=f"View query failed to execute: {e}",
                    code="query_execution_error",
                )
            )

        return errors, translated
