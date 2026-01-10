"""Pydantic schemas for email template API endpoints.

Defines request and response models for email template management.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailTemplateResponse(BaseModel):
    """Response schema for email template data.

    Attributes:
        id: Template ID (UUID string).
        account_id: Account ID this template belongs to.
        template_type: Template type identifier (e.g., 'email_verification').
        locale: Language/locale code (e.g., 'en', 'es').
        subject: Email subject line with Jinja2 variables.
        html_body: HTML email body with Jinja2 variables.
        text_body: Plain text email body with Jinja2 variables.
        enabled: Whether this template is active.
        is_builtin: Whether this is a built-in system template.
        created_at: Timestamp when the template was created.
        updated_at: Timestamp when the template was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    template_type: str
    locale: str
    subject: str
    html_body: str
    text_body: str
    enabled: bool
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


class EmailTemplateUpdate(BaseModel):
    """Request schema for updating an email template.

    Attributes:
        subject: Optional new subject line.
        html_body: Optional new HTML body.
        text_body: Optional new plain text body.
        enabled: Optional new enabled status.
    """

    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None
    enabled: bool | None = None


class EmailTemplateTestRequest(BaseModel):
    """Request schema for sending a test email.

    Attributes:
        recipient_email: Email address to send test email to.
        variables: Optional dictionary of variables for template rendering.
    """

    recipient_email: EmailStr
    variables: dict[str, str] = Field(default_factory=dict)
    provider: str | None = None


class EmailTemplateRenderRequest(BaseModel):
    """Request schema for rendering a template without sending.

    Attributes:
        template_type: Template type to render (e.g., 'email_verification').
        variables: Dictionary of variables for template rendering.
        locale: Optional language/locale code (default: 'en').
        account_id: Optional account ID for template lookup.
    """

    template_type: str
    variables: dict[str, str]
    locale: str = "en"
    account_id: str | None = None
    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None


class EmailTemplateRenderResponse(BaseModel):
    """Response schema for rendered template content.

    Attributes:
        subject: Rendered subject line.
        html_body: Rendered HTML body.
        text_body: Rendered plain text body.
    """

    subject: str
    html_body: str
    text_body: str


class EmailLogResponse(BaseModel):
    """Response schema for email log data.

    Attributes:
        id: Log ID (UUID string).
        account_id: Account ID this log belongs to.
        template_type: Template type used (e.g., 'email_verification').
        recipient_email: Email address of the recipient.
        provider: Email provider used (e.g., 'smtp', 'ses', 'resend').
        status: Delivery status ('sent', 'failed', 'pending').
        error_message: Error message if status is 'failed' (nullable).
        variables: Template variables used for rendering (nullable).
        sent_at: Timestamp when the email was sent or attempted.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    template_type: str
    recipient_email: str
    provider: str
    status: str
    error_message: str | None = None
    variables: dict[str, str] | None = None
    sent_at: datetime


class EmailLogListResponse(BaseModel):
    """Response schema for paginated email log list.

    Attributes:
        logs: List of email logs.
        total: Total number of logs matching the filters.
        page: Current page number.
        page_size: Number of logs per page.
    """

    logs: list[EmailLogResponse]
    total: int
    page: int
    page_size: int

