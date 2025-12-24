"""API router for managing SQL macros."""

import time
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
    MacroTestRequest,
    MacroTestResponse,
    MacroUpdate,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)
from snackbase.infrastructure.persistence.repositories.permission_repository import (
    PermissionRepository,
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


@router.post(
    "/{macro_id}/test",
    response_model=MacroTestResponse,
    dependencies=[Depends(require_superadmin)],
)
async def test_macro(
    macro_id: int,
    test_request: MacroTestRequest,
    current_user: SuperadminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Test a SQL macro execution.

    Executes the macro in a transaction that is rolled back after execution.
    Requires superadmin privileges.
    """
    from sqlalchemy import text
    import json

    repository = MacroRepository(db)
    macro = await repository.get_by_id(macro_id)
    
    if not macro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macro not found",
        )
    
    # Parse macro parameters
    try:
        param_names = json.loads(macro.parameters) if macro.parameters else []
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid macro parameters definition",
        )
    
    # Validate parameter count
    if len(test_request.parameters) != len(param_names):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Expected {len(param_names)} parameters, got {len(test_request.parameters)}",
        )
    
    # Build bind parameters
    bind_params = {}
    for i, param_name in enumerate(param_names):
        bind_params[param_name] = test_request.parameters[i]
    
    # Execute in transaction with rollback
    try:
        # Start a savepoint for rollback
        async with db.begin_nested():
            start_time = time.time()
            
            stmt = text(macro.sql_query)
            stmt = stmt.bindparams(**bind_params)
            
            # Execute with timeout
            stmt = stmt.execution_options(timeout=5)
            result = await db.execute(stmt)
            
            # Get result
            result_value = result.scalar()
            
            # Calculate execution time in milliseconds
            execution_time = (time.time() - start_time) * 1000
            
            # Rollback the nested transaction
            raise Exception("Rollback test transaction")
            
    except Exception as e:
        # Expected rollback or actual error
        if "Rollback test transaction" not in str(e):
            logger.error(
                "Macro test execution failed",
                macro_id=macro_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Macro execution failed: {str(e)}",
            )
    
    logger.info(
        "Macro tested",
        macro_id=macro_id,
        execution_time=execution_time,
        user_id=current_user.user_id,
    )
    
    return MacroTestResponse(
        result=str(result_value) if result_value is not None else None,
        execution_time=execution_time,
        rows_affected=0,  # SELECT queries don't affect rows
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
    Fails if macro is used in any active permission rules.
    """
    macro_repo = MacroRepository(db)
    permission_repo = PermissionRepository(db)
    
    # Check if macro exists
    macro = await macro_repo.get_by_id(macro_id)
    if not macro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macro not found",
        )
    
    # Check if macro is used in any permissions
    permissions_using_macro = await permission_repo.find_permissions_using_macro(macro.name)
    if permissions_using_macro:
        logger.warning(
            "Cannot delete macro: in use by permissions",
            macro_id=macro_id,
            macro_name=macro.name,
            permission_count=len(permissions_using_macro),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete macro '{macro.name}': it is used in {len(permissions_using_macro)} permission rule(s)",
        )
    
    # Delete the macro
    deleted = await macro_repo.delete(macro_id)
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
