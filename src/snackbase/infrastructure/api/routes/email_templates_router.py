"""Email template management API routes.

Provides endpoints for CRUD operations on email templates, template rendering,
and test email sending.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.api.schemas.email_schemas import (
    EmailLogListResponse,
    EmailLogResponse,
    EmailTemplateRenderRequest,
    EmailTemplateRenderResponse,
    EmailTemplateResponse,
    EmailTemplateTestRequest,
    EmailTemplateUpdate,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.persistence.repositories.email_log_repository import (
    EmailLogRepository,
)
from snackbase.infrastructure.persistence.repositories.email_template_repository import (
    EmailTemplateRepository,
)
from snackbase.infrastructure.services.email_service import EmailService

router = APIRouter(tags=["admin", "email"])
logger = get_logger(__name__)


@router.get("/templates")
async def list_email_templates(
    _admin: SuperadminUser,
    template_type: str | None = None,
    locale: str | None = None,
    account_id: str | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[EmailTemplateResponse]:
    """List all email templates with optional filters.

    Args:
        template_type: Optional filter by template type.
        locale: Optional filter by locale.
        account_id: Optional filter by account ID.
        enabled: Optional filter by enabled status.

    Returns:
        List of email templates matching the filters.
    """
    try:
        repo = EmailTemplateRepository()
        templates = await repo.list_templates(
            session=db,
            account_id=account_id,
            template_type=template_type,
            locale=locale,
            enabled=enabled,
        )

        return [EmailTemplateResponse.model_validate(t) for t in templates]

    except Exception as e:
        logger.error("Failed to list email templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list email templates",
        )


@router.get("/templates/{template_id}")
async def get_email_template(
    _admin: SuperadminUser,
    template_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> EmailTemplateResponse:
    """Get email template by ID.

    Args:
        template_id: Template ID to retrieve.

    Returns:
        Email template details.

    Raises:
        HTTPException: 404 if template not found.
    """
    try:
        repo = EmailTemplateRepository()
        template = await repo.get_by_id(session=db, template_id=template_id)

        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        return EmailTemplateResponse.model_validate(template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get email template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email template",
        )


@router.put("/templates/{template_id}")
async def update_email_template(
    _admin: SuperadminUser,
    template_id: str,
    update_data: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> EmailTemplateResponse:
    """Update an email template.

    Args:
        template_id: Template ID to update.
        update_data: Fields to update.

    Returns:
        Updated email template.

    Raises:
        HTTPException: 404 if template not found.
    """
    try:
        repo = EmailTemplateRepository()
        template = await repo.get_by_id(session=db, template_id=template_id)

        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        # Update fields if provided
        if update_data.subject is not None:
            template.subject = update_data.subject
        if update_data.html_body is not None:
            template.html_body = update_data.html_body
        if update_data.text_body is not None:
            template.text_body = update_data.text_body
        if update_data.enabled is not None:
            template.enabled = update_data.enabled

        # Save changes
        updated_template = await repo.update(session=db, template=template)
        await db.commit()

        logger.info(
            "Email template updated",
            template_id=template_id,
            template_type=template.template_type,
        )

        return EmailTemplateResponse.model_validate(updated_template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update email template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email template",
        )


@router.post("/templates/render")
async def render_email_template(
    _admin: SuperadminUser,
    render_request: EmailTemplateRenderRequest,
    db: AsyncSession = Depends(get_db_session),
) -> EmailTemplateRenderResponse:
    """Render an email template without sending.

    Args:
        render_request: Template rendering request with variables.

    Returns:
        Rendered email content (subject, html_body, text_body).

    Raises:
        HTTPException: 404 if template not found, 422 if rendering fails.
    """
    try:
        # Get template repository
        template_repo = EmailTemplateRepository()

        # Determine account_id (use system account if not provided)
        account_id = render_request.account_id or template_repo.SYSTEM_ACCOUNT_ID

        # Get template
        template = await template_repo.get_template(
            session=db,
            account_id=account_id,
            template_type=render_request.template_type,
            locale=render_request.locale,
        )

        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {render_request.template_type} "
                f"(locale: {render_request.locale})",
            )

        # Render template
        from snackbase.infrastructure.services.email.template_renderer import (
            get_template_renderer,
        )

        renderer = get_template_renderer()

        try:
            # Use provided content or fallback to template content
            raw_subject = render_request.subject if render_request.subject is not None else template.subject
            raw_html = render_request.html_body if render_request.html_body is not None else template.html_body
            raw_text = render_request.text_body if render_request.text_body is not None else template.text_body

            subject = renderer.render(raw_subject, render_request.variables)
            html_body = renderer.render(raw_html, render_request.variables)
            text_body = renderer.render(raw_text, render_request.variables)
        except Exception as e:
            logger.error(
                "Template rendering failed",
                template_type=render_request.template_type,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Template rendering failed: {str(e)}",
            )

        return EmailTemplateRenderResponse(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to render email template",
            template_type=render_request.template_type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render email template",
        )


@router.post("/templates/{template_id}/test")
async def send_test_email(
    _admin: SuperadminUser,
    template_id: str,
    test_request: EmailTemplateTestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Send a test email using the specified template.

    Args:
        template_id: Template ID to use for test email.
        test_request: Test email request with recipient and variables.
        request: FastAPI request object for accessing app state.

    Returns:
        Success message with email details.

    Raises:
        HTTPException: 404 if template not found, 400 if no email provider configured,
                      500 if sending fails.
    """
    try:
        # Get template
        template_repo = EmailTemplateRepository()
        template = await template_repo.get_by_id(session=db, template_id=template_id)

        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        # Initialize email service with encryption service
        config_repo = ConfigurationRepository(db)
        log_repo = EmailLogRepository()
        registry = request.app.state.config_registry
        
        email_service = EmailService(
            template_repository=template_repo,
            log_repository=log_repo,
            config_repository=config_repo,
            encryption_service=registry.encryption_service,
        )

        # Send test email (provider selection is automatic)
        success = await email_service.send_template_email(
            session=db,
            to=test_request.recipient_email,
            template_type=template.template_type,
            variables=test_request.variables,
            account_id=template.account_id,
            locale=template.locale,
            provider_name=test_request.provider,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email",
            )

        logger.info(
            "Test email sent successfully",
            template_id=template_id,
            recipient=test_request.recipient_email,
        )

        return {
            "status": "success",
            "message": f"Test email sent to {test_request.recipient_email}",
            "template_type": template.template_type,
            "locale": template.locale,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to send test email",
            template_id=template_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}",
        )


@router.get("/logs")
async def list_email_logs(
    _admin: SuperadminUser,
    status_filter: str | None = None,
    template_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: AsyncSession = Depends(get_db_session),
) -> EmailLogListResponse:
    """List email logs with optional filters and pagination.

    Args:
        status_filter: Optional filter by status ('sent', 'failed', 'pending').
        template_type: Optional filter by template type.
        start_date: Optional filter by start date (ISO format).
        end_date: Optional filter by end date (ISO format).
        page: Page number (default: 1).
        page_size: Number of logs per page (default: 25, max: 100).

    Returns:
        Paginated list of email logs.
    """
    try:
        from datetime import datetime

        # Validate and limit page_size
        page_size = min(page_size, 100)
        offset = (page - 1) * page_size

        # Parse dates if provided
        start_datetime = None
        end_datetime = None
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid start_date format: {start_date}",
                )
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid end_date format: {end_date}",
                )

        # Get logs from repository
        log_repo = EmailLogRepository()
        logs, total = await log_repo.list_logs(
            session=db,
            status=status_filter,
            template_type=template_type,
            start_date=start_datetime,
            end_date=end_datetime,
            limit=page_size,
            offset=offset,
        )

        return EmailLogListResponse(
            logs=[EmailLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list email logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list email logs",
        )


@router.get("/logs/{log_id}")
async def get_email_log(
    _admin: SuperadminUser,
    log_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> EmailLogResponse:
    """Get email log by ID.

    Args:
        log_id: Log ID to retrieve.

    Returns:
        Email log details.

    Raises:
        HTTPException: 404 if log not found.
    """
    try:
        log_repo = EmailLogRepository()
        log = await log_repo.get_by_id(session=db, log_id=log_id)

        if log is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email log not found: {log_id}",
            )

        return EmailLogResponse.model_validate(log)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get email log", log_id=log_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email log",
        )

