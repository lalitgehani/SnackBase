"""Audit log API routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas.audit_log_schemas import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogExportFormat,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.domain.services.audit_log_service import AuditLogService

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=AuditLogListResponse,
    responses={
        403: {"description": "Superadmin access required"},
    },
)
async def list_audit_logs(
    current_user: SuperadminUser,
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    record_id: Optional[str] = Query(None, description="Filter by record ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    operation: Optional[str] = Query(None, description="Filter by operation (CREATE, UPDATE, DELETE)"),
    from_date: Optional[datetime] = Query(None, description="Filter from this timestamp (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Filter to this timestamp (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Number of entries to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of entries to return"),
    sort_by: str = Query("occurred_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order (asc or desc)"),
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    """List audit log entries with advanced filtering and pagination.

    Only superadmins can access audit logs.
    """
    audit_service = AuditLogService(session)
    logs, total = await audit_service.list_logs(
        account_id=account_id,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        operation=operation,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/export",
    responses={
        200: {
            "content": {"text/csv": {}, "application/json": {}},
            "description": "Exported audit logs",
        },
        403: {"description": "Superadmin access required"},
    },
)
async def export_audit_logs(
    current_user: SuperadminUser,
    format: AuditLogExportFormat = Query(AuditLogExportFormat.CSV, description="Export format"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    record_id: Optional[str] = Query(None, description="Filter by record ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    from_date: Optional[datetime] = Query(None, description="Filter from this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter to this timestamp"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Export audit logs in CSV or JSON format.

    Applies current filters to the exported data.
    Only superadmins can export audit logs.
    """
    audit_service = AuditLogService(session)
    content, media_type = await audit_service.export_logs(
        format=format.value,
        account_id=account_id,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        operation=operation,
        from_date=from_date,
        to_date=to_date,
    )

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    return Response(content=content, media_type=media_type, headers=headers)


@router.get(
    "/{log_id}",
    status_code=status.HTTP_200_OK,
    response_model=AuditLogResponse,
    responses={
        403: {"description": "Superadmin access required"},
        404: {"description": "Audit log entry not found"},
    },
)
async def get_audit_log(
    log_id: int,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogResponse:
    """Get a single audit log entry by ID.

    Includes full details and integrity chain information.
    Only superadmins can access audit logs.
    """
    audit_service = AuditLogService(session)
    log = await audit_service.get_log_by_id(log_id)

    if not log:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry {log_id} not found",
        )

    return AuditLogResponse.model_validate(log)
