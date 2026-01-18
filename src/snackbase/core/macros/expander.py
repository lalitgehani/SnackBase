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
        self.builtin_macros = {
            "owns_record": "created_by = @request.auth.id",
            "is_public": "public = true",
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
        offset = 0
        
        # We use finditer so we can handle matches one by one and replace them
        # Note: we need to re-scan the result if we want recursive expansion, 
        # or just expand the replacement and then stick it in.
        # Expanding the replacement before insertion is cleaner for recursion.
        
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

            # 1. Expand built-in
            replacement = None
            if macro_name in self.builtin_macros:
                replacement = self.builtin_macros[macro_name]
            
            # 2. Expand database macro
            elif self.macro_repo:
                db_macro = await self.macro_repo.get_by_name(macro_name)
                if db_macro:
                    replacement = db_macro.sql_query
                    # Handle parameters ($1, $2, etc.)
                    if args:
                        for i, arg in enumerate(args):
                            placeholder = f"${i+1}"
                            replacement = replacement.replace(placeholder, arg)

            if replacement is not None:
                # Recursively expand the replacement
                expanded_replacement = await self.expand(replacement, depth + 1)
                # Wrap in parentheses for safety
                wrapped_replacement = f"({expanded_replacement})"
                
                # Replace in original string
                start, end = match.span()
                result = result[:start] + wrapped_replacement + result[end:]
                
        return result
