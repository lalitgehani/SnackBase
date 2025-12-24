"""API router for managing SQL macros."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import (
    AuthenticatedUser,
    SuperadminUser,
    get_current_user,
    require_superadmin,
)
from snackbase.infrastructure.api.schemas.macro import (
    MacroCreate,
    MacroResponse,
    MacroUpdate,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/",
    response_model=MacroResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin)],
)
async def create_macro(
    macro_in: MacroCreate,
    current_user: SuperadminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new SQL macro.

    Requires superadmin privileges.
    """
    repository = MacroRepository(db)
    try:
        macro = await repository.create(
            name=macro_in.name,
            sql_query=macro_in.sql_query,
            parameters=macro_in.parameters,
            description=macro_in.description,
            created_by=current_user.user_id,
        )
        logger.info(
            "Macro created",
            macro_name=macro.name,
            user_id=current_user.user_id,
        )
        return macro
    except IntegrityError:
        logger.warning(
            "Macro creation failed: name already exists",
            macro_name=macro_in.name,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Macro with name '{macro_in.name}' already exists",
        )


@router.get(
    "/",
    response_model=List[MacroResponse],
    dependencies=[Depends(get_current_user)],
)
async def list_macros(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List all SQL macros.

    Accessible by all authenticated users.
    """
    repository = MacroRepository(db)
    macros = await repository.list_all(skip=skip, limit=limit)
    return macros


@router.get(
    "/{macro_id}",
    response_model=MacroResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_macro(
    macro_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a SQL macro by ID.

    Accessible by all authenticated users.
    """
    repository = MacroRepository(db)
    macro = await repository.get_by_id(macro_id)
    if not macro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macro not found",
        )
    return macro


@router.put(
    "/{macro_id}",
    response_model=MacroResponse,
    dependencies=[Depends(require_superadmin)],
)
async def update_macro(
    macro_id: int,
    macro_in: MacroUpdate,
    current_user: SuperadminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a SQL macro.

    Requires superadmin privileges.
    """
    repository = MacroRepository(db)
    try:
        macro = await repository.update(
            macro_id=macro_id,
            name=macro_in.name,
            sql_query=macro_in.sql_query,
            parameters=macro_in.parameters,
            description=macro_in.description,
        )
        if not macro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Macro not found",
            )
        
        logger.info(
            "Macro updated",
            macro_id=macro_id,
            user_id=current_user.user_id,
        )
        return macro
    except IntegrityError:
         logger.warning(
            "Macro update failed: name collision",
            macro_id=macro_id,
            new_name=macro_in.name,
        )
         raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Macro with name '{macro_in.name}' already exists",
        )


@router.delete(
    "/{macro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_superadmin)],
)
async def delete_macro(
    macro_id: int,
    current_user: SuperadminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a SQL macro.

    Requires superadmin privileges.
    """
    repository = MacroRepository(db)
    deleted = await repository.delete(macro_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macro not found",
        )
    
    logger.info(
        "Macro deleted",
        macro_id=macro_id,
        user_id=current_user.user_id,
    )
