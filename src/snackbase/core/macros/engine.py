"""Macro Execution Engine."""

import json
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import TextClause

from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)


class MacroType(Enum):
    """Types of macros."""

    BUILTIN = "builtin"
    SQL = "sql"


class MacroExecutionEngine:
    """Engine for executing macros safely."""

    def __init__(self, session: AsyncSession | None = None):
        """Initialize the engine.

        Args:
            session: SQLAlchemy async session. Optional, required only for SQL macros.
        """
        self.session = session
        if session:
            self.macro_repo = MacroRepository(session)
        else:
            self.macro_repo = None

    async def execute_macro(
        self, name: str, args: list[Any], context: dict[str, Any]
    ) -> Any:
        """Execute a macro by name.

        Args:
            name: The macro name (including @).
            args: List of arguments passed to the macro.
            context: The evaluation context (user, record, etc.).

        Returns:
            The result of the macro execution.
        """
        # 1. Check for built-in macros
        if name.startswith("@"):
            if name == "@has_group":
                return self._execute_has_group(args, context)
            if name == "@has_role":
                return self._execute_has_role(args, context)
            if name in ("@owns_record", "@is_creator"):
                return self._execute_owns_record(args, context)
            if name == "@in_time_range":
                return self._execute_in_time_range(args, context)
            if name == "@has_permission":
                return self._execute_has_permission(args, context)

        # 2. Check for SQL macros
        if not self.macro_repo:
            return False

        lookup_name = name
        if lookup_name.startswith("@"):
            lookup_name = lookup_name[1:]
            
        macro = await self.macro_repo.get_by_name(lookup_name)
        if not macro:
            # Try with @ just in case
            macro = await self.macro_repo.get_by_name(name)
            
        if macro:
            return await self._execute_sql_macro(macro, args, context)

        # 3. Macro not found
        # We return False (deny) by default for safety, or raise error?
        # Requirement: "Error in query returns false (deny)" -> likely applies here too
        # But maybe we should log it.
        return False

    def _execute_has_group(self, args: list[Any], context: dict[str, Any]) -> bool:
        """Check if user has a group."""
        if len(args) != 1:
            return False
        group_name = args[0]
        user = context.get("user")
        if not user:
            return False
            
        groups = []
        if isinstance(user, dict):
            groups = user.get("groups", [])
        else:
            groups = getattr(user, "groups", [])
            
        if not groups:
            return False
            
        return group_name in groups

    def _execute_has_role(self, args: list[Any], context: dict[str, Any]) -> bool:
        """Check if user has a role."""
        if len(args) != 1:
            return False
        role_name = args[0]
        user = context.get("user")
        if not user:
            return False
            
        role = None
        if isinstance(user, dict):
            role = user.get("role")
        else:
            role = getattr(user, "role", None)
            
        return role == role_name

    def _execute_owns_record(self, args: list[Any], context: dict[str, Any]) -> bool:
        """Check if user owns the record."""
        if len(args) != 0:
            return False
            
        user = context.get("user")
        record = context.get("record")
        
        if not user or not record:
            return False
            
        user_id = None
        if isinstance(user, dict):
            user_id = user.get("id")
        else:
            user_id = getattr(user, "id", None)
            
        owner_id = None
        if isinstance(record, dict):
            owner_id = record.get("owner_id")
        else:
            owner_id = getattr(record, "owner_id", None)
            
        if user_id is None or owner_id is None:
            return False
            
        return str(user_id) == str(owner_id)

    def _execute_in_time_range(self, args: list[Any], context: dict[str, Any]) -> bool:
        """Check if current time is in range (UTC)."""
        from datetime import datetime, timezone
        
        if len(args) != 2:
            return False
        
        try:
            start_hour = float(args[0])
            end_hour = float(args[1])
            current_hour = datetime.now(timezone.utc).hour
            return start_hour <= current_hour < end_hour
        except (ValueError, TypeError):
            return False

    def _execute_has_permission(self, args: list[Any], context: dict[str, Any]) -> bool:
        """Check specific permission."""
        if len(args) != 2:
            return False
            
        action = args[0]
        collection = args[1]
        
        permissions = context.get("permissions")
        if not permissions or not isinstance(permissions, dict):
            return False
            
        collection_perms = permissions.get(collection)
        if not collection_perms or not isinstance(collection_perms, list):
            return False
            
        return action in collection_perms

    async def _execute_sql_macro(
        self, macro: Any, args: list[Any], context: dict[str, Any]
    ) -> Any:
        """Execute a SQL macro with parameter substitution."""
        # 0. Check Cache
        # We cache based on macro name and args. Context is implicitly used via args if passed.
        # If context implicitly affects query (e.g. RLS), then caching might be risky if not keyed by context?
        # But macros are simple SELECTs. If arguments are the same, result should be same for the same request.
        # We assume MacroExecutionEngine is scoped to a request.
        
        # Create cache key
        cache_key = (macro.name, tuple(args))
        
        # Check if we have a cache
        if not hasattr(self, "_cache"):
            self._cache = {}
            
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Parse stored parameters
        param_names: list[str] = []
        try:
            if macro.parameters:
                param_names = json.loads(macro.parameters)
        except json.JSONDecodeError:
            return False # Invalid macro definition

        # 2. Validate argument count
        if len(args) != len(param_names):
            return False

        # 3. Build bind parameters
        bind_params = {}
        for i, param_name in enumerate(param_names):
            bind_params[param_name] = args[i]
            
        # 4. Execute Query
        try:
            stmt = text(macro.sql_query)
            # Bind parameters
            stmt = stmt.bindparams(**bind_params)
            
            # Enforce 5 second timeout
            stmt = stmt.execution_options(timeout=5)
            
            result = await self.session.execute(stmt)
            val = result.scalar()
            
            # Cache result
            self._cache[cache_key] = val
            
            return val
            
        except Exception:
            return False
