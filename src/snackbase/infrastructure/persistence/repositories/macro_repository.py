"""Repository for accessing and managing macros."""

import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.macro import MacroModel


class MacroRepository:
    """Repository for managing Macro entities."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(
        self,
        name: str,
        sql_query: str,
        parameters: list[str] | None = None,
        description: str | None = None,
        created_by: str | None = None,
    ) -> MacroModel:
        """Create a new macro.

        Args:
            name: Unique name of the macro.
            sql_query: The SQL SELECT query.
            parameters: List of parameter names.
            description: Optional description.
            created_by: User ID of the creator.

        Returns:
            The created MacroModel.

        Raises:
            IntegrityError: If a macro with the same name already exists.
        """
        params_json = json.dumps(parameters) if parameters else "[]"
        macro = MacroModel(
            name=name,
            sql_query=sql_query,
            parameters=params_json,
            description=description,
            created_by=created_by,
        )
        self.session.add(macro)
        await self.session.commit()
        await self.session.refresh(macro)
        return macro

    async def get_by_id(self, macro_id: int) -> MacroModel | None:
        """Get a macro by ID.

        Args:
            macro_id: The macro ID.

        Returns:
            The MacroModel or None if not found.
        """
        stmt = select(MacroModel).where(MacroModel.id == macro_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> MacroModel | None:
        """Get a macro by name.

        Args:
            name: The macro name.

        Returns:
            The MacroModel or None if not found.
        """
        stmt = select(MacroModel).where(MacroModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[MacroModel]:
        """List macros with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of MacroModel instances.
        """
        stmt = select(MacroModel).offset(skip).limit(limit).order_by(MacroModel.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        macro_id: int,
        name: str | None = None,
        sql_query: str | None = None,
        parameters: list[str] | None = None,
        description: str | None = None,
    ) -> MacroModel | None:
        """Update a macro.

        Args:
            macro_id: The macro ID.
            name: New name (optional).
            sql_query: New SQL query (optional).
            parameters: New parameters list (optional).
            description: New description (optional).

        Returns:
            The updated MacroModel or None if not found.
        """
        macro = await self.get_by_id(macro_id)
        if not macro:
            return None

        if name is not None:
            macro.name = name
        if sql_query is not None:
            macro.sql_query = sql_query
        if parameters is not None:
            macro.parameters = json.dumps(parameters)
        if description is not None:
            macro.description = description

        await self.session.commit()
        await self.session.refresh(macro)
        return macro

    async def delete(self, macro_id: int) -> bool:
        """Delete a macro.

        Args:
            macro_id: The macro ID.

        Returns:
            True if deleted, False if not found.
        """
        macro = await self.get_by_id(macro_id)
        if not macro:
            return False

        await self.session.delete(macro)
        await self.session.commit()
        return True
