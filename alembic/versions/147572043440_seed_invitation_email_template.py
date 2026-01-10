"""seed_invitation_email_template

Revision ID: 147572043440
Revises: 0ea276bf29bc
Create Date: 2026-01-10 22:19:02.935942

"""
import uuid
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '147572043440'
down_revision: str | Sequence[str] | None = '0ea276bf29bc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
INVITATION_TEMPLATE_ID = "44444444-4444-4444-4444-444444444444"  # Deterministic ID for migration

HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You've been invited</title>
    <style>
        @media only screen and (max-width: 600px) {
            .container { padding: 10px !important; }
            .button { padding: 10px 20px !important; font-size: 14px !important; }
            h1 { font-size: 24px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px;">
                    <!-- Header -->
                    <tr>
                        <td style="text-align: center; padding-bottom: 30px;">
                            <h1 style="margin: 0; color: #2c3e50; font-size: 28px; font-weight: 600;">{{ app_name }}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td>
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">You've been invited to join {{ account_name }}</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello,</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">You have been invited by <strong style="color: #2c3e50;">{{ invited_by }}</strong> to join the team <strong style="color: #2c3e50;">{{ account_name }}</strong> on {{ app_name }}.</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">To accept the invitation and set up your account, please click the button below:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ invitation_url }}" class="button" style="display: inline-block; background-color: #3498db; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(52,152,219,0.3);">Accept Invitation</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #3498db; font-size: 14px;">{{ invitation_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #f7fafc; padding: 16px; border-radius: 6px; border-left: 4px solid #3498db;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Invitation Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This invitation will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">If you were not expecting this invitation, you can safely ignore this email.</p>
                            <p style="margin: 0; color: #a0aec0; font-size: 13px;">Need help? Visit <a href="{{ app_url }}" style="color: #3498db; text-decoration: none;">{{ app_name }}</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
""".strip()

TEXT_BODY = """
{{ app_name }} - Invitation to join {{ account_name }}

Hello,

You have been invited by {{ invited_by }} to join the team {{ account_name }} on {{ app_name }}.

To accept the invitation and set up your account, please visit the following link:

{{ invitation_url }}

{% if token %}Invitation Code: {{ token }}{% endif %}

{% if expires_at %}This invitation will expire on {{ expires_at }}.{% endif %}

If you were not expecting this invitation, you can safely ignore this email.

Need help? Visit {{ app_url }}
""".strip()

def upgrade() -> None:
    """Upgrade schema."""
    # Insert the invitation template
    op.execute(
        sa.text(
            "INSERT INTO email_templates "
            "(id, account_id, template_type, locale, subject, html_body, text_body, is_builtin, created_at, updated_at) "
            "VALUES "
            "(:id, :account_id, :template_type, :locale, :subject, :html_body, :text_body, :is_builtin, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(
            id=INVITATION_TEMPLATE_ID,
            account_id=SYSTEM_ACCOUNT_ID,
            template_type='invitation',
            locale='en',
            subject="You've been invited to join {{ account_name }}",
            html_body=HTML_BODY,
            text_body=TEXT_BODY,
            is_builtin=True
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the invitation template
    op.execute(
        sa.text(
            "DELETE FROM email_templates "
            "WHERE id = :id"
        ).bindparams(
            id=INVITATION_TEMPLATE_ID
        )
    )
