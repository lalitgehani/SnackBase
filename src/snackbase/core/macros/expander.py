"""Macro Expansion Engine for Permission Rules.

Performs text substitution of macros in rule expressions before parsing.
Supports built-in macros, database-defined macros, and positional parameters.
"""

import re
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.repositories.macro_repository import MacroRepository
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

# Pattern to match macros: @name or @name(arg1, arg2, ...)
MACRO_PATTERN = re.compile(r"@([a-zA-Z_][a-zA-Z0-9_]*)(?:\((.*?)\))?")

class MacroExpander:
    """Expands macros in rule expressions via text substitution."""

    MAX_RECURSION_DEPTH = 3

    def __init__(self, session: AsyncSession | None = None):
        """Initialize the expander.

        Args:
            session: SQLAlchemy async session for database macro lookups.
        """
        self.session = session
        self.macro_repo = MacroRepository(session) if session else None
        
        # Built-in macro definitions (mapping name -> substitution fragment)
        # Fragments can use $1, $2, etc. for parameters
        self.builtin_macros = {
            "owns_record": "created_by = @request.auth.id",
            "is_creator": "created_by = @request.auth.id",
            "is_public": "public = true",
            "has_role": "@request.auth.role = $1",
            "has_group": "exists(select 1 from users_groups ug join groups g on ug.group_id = g.id where ug.user_id = @request.auth.id and g.name = $1)",
        }

    async def expand(self, expression: str, depth: int = 0) -> str:
        """Recursively expand macros in the given expression.

        Args:
            expression: The rule expression to expand.
            depth: Current recursion depth.

        Returns:
            The expanded expression.

        Raises:
            RecursionError: If max recursion depth is exceeded.
        """
        if depth > self.MAX_RECURSION_DEPTH:
            logger.error("Max macro recursion depth exceeded", expression=expression)
            raise RecursionError(f"Max macro recursion depth of {self.MAX_RECURSION_DEPTH} exceeded")

        if not expression or not "@" in expression:
            return expression

        # Find all macro occurrences
        result = expression
        
        matches = list(MACRO_PATTERN.finditer(expression))
        # Process in reverse to maintain offsets
        for match in reversed(matches):
            macro_full = match.group(0)
            macro_name = match.group(1)
            macro_args_str = match.group(2)
            
            # Split arguments by comma and strip whitespace
            args = []
            if macro_args_str:
                # Basic comma split, doesn't handle nested parens or escaped commas well
                # but should be enough for simple macros.
                args = [arg.strip() for arg in macro_args_str.split(",")]

            # 1. Look for replacement template
            replacement_template = None
            if macro_name in self.builtin_macros:
                replacement_template = self.builtin_macros[macro_name]
            elif self.macro_repo:
                db_macro = await self.macro_repo.get_by_name(macro_name)
                if db_macro:
                    replacement_template = db_macro.sql_query

            if replacement_template is not None:
                # Apply parameters ($1, $2, etc.)
                replacement = replacement_template
                if args:
                    for i, arg in enumerate(args):
                        placeholder = f"${i+1}"
                        replacement = replacement.replace(placeholder, arg)
                
                # Special case for @owns_record(field_name)
                if macro_name == "owns_record" and args:
                    replacement = f"{args[0]} = @request.auth.id"

                # Recursively expand the replacement
                expanded_replacement = await self.expand(replacement, depth + 1)
                # Wrap in parentheses for safety
                wrapped_replacement = f"({expanded_replacement})"
                
                # Replace in original string
                start, end = match.span()
                result = result[:start] + wrapped_replacement + result[end:]
                
        return result
