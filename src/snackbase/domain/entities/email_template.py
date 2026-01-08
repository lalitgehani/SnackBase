"""Email template entity for storing email templates.

Email templates are used to send transactional emails with variable substitution.
Templates can be customized per account or use system-level defaults.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class EmailTemplate:
    """Email template entity representing a customizable email template.

    Templates support Jinja2 variable substitution and can be localized.
    System-level templates (is_builtin=true) cannot be deleted.

    Attributes:
        id: Unique identifier (UUID string).
        account_id: Foreign key to the account this template belongs to.
        template_type: Template type identifier (e.g., 'email_verification', 'password_reset').
        locale: Language/locale code (e.g., 'en', 'es', 'fr').
        subject: Email subject line (supports Jinja2 variables).
        html_body: HTML email body (supports Jinja2 variables).
        text_body: Plain text email body (supports Jinja2 variables).
        enabled: Whether this template is active.
        is_builtin: Whether this is a built-in system template (cannot be deleted).
        created_at: Timestamp when the template was created.
        updated_at: Timestamp when the template was last updated.
    """

    id: str
    account_id: str
    template_type: str
    locale: str
    subject: str
    html_body: str
    text_body: str
    enabled: bool = True
    is_builtin: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate email template data after initialization."""
        if not self.id:
            raise ValueError("Email template ID is required")
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.template_type:
            raise ValueError("Template type is required")
        if not self.locale:
            raise ValueError("Locale is required")
        if not self.subject:
            raise ValueError("Subject is required")
        if not self.html_body:
            raise ValueError("HTML body is required")
        if not self.text_body:
            raise ValueError("Text body is required")
