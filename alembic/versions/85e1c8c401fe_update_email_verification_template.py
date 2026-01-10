"""update_email_verification_template

Revision ID: 85e1c8c401fe
Revises: def3fc1039eb
Create Date: 2026-01-10 15:24:57.208396

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "85e1c8c401fe"
down_revision: str | Sequence[str] | None = "def3fc1039eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

NEW_HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
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
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Verify Your Email Address</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello,</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">We received a request to create an account for <strong style="color: #2c3e50;">{{ email }}</strong>.</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">To complete your registration and start using {{ app_name }}, please verify your email address by clicking the button below:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ verification_url }}" class="button" style="display: inline-block; background-color: #3498db; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(52,152,219,0.3);">Verify Email Address</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #3498db; font-size: 14px;">{{ verification_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #f7fafc; padding: 16px; border-radius: 6px; border-left: 4px solid #3498db;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Verification Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This verification link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">If you didn't create an account with {{ app_name }} using this email address, you can safely ignore this email.</p>
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

NEW_TEXT_BODY = """
{{ app_name }} - Verify Your Email Address

Hello,

We received a request to create an account for {{ email }}.

To complete your registration and start using {{ app_name }}, please verify your email address by visiting the following link:

{{ verification_url }}

{% if token %}Verification Code: {{ token }}{% endif %}

{% if expires_at %}This verification link will expire on {{ expires_at }}.{% endif %}

If you didn't create an account with {{ app_name }} using this email address, you can safely ignore this email.

Need help? Visit {{ app_url }}
""".strip()

OLD_HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
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
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Verify Your Email Address</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Thank you for signing up for {{ app_name }}! To complete your registration and start using your account, please verify your email address by clicking the button below:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ verification_url }}" class="button" style="display: inline-block; background-color: #3498db; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(52,152,219,0.3);">Verify Email Address</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #3498db; font-size: 14px;">{{ verification_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #f7fafc; padding: 16px; border-radius: 6px; border-left: 4px solid #3498db;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Verification Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This verification link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">If you didn't create an account with {{ app_name }}, you can safely ignore this email.</p>
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

OLD_TEXT_BODY = """
{{ app_name }} - Verify Your Email Address

Hello{% if user_name %} {{ user_name }}{% endif %},

Thank you for signing up for {{ app_name }}! To complete your registration and start using your account, please verify your email address by visiting the following link:

{{ verification_url }}

{% if token %}Verification Code: {{ token }}{% endif %}

{% if expires_at %}This verification link will expire on {{ expires_at }}.{% endif %}

If you didn't create an account with {{ app_name }}, you can safely ignore this email.

Need help? Visit {{ app_url }}
""".strip()

def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE email_templates "
            "SET html_body = :html_body, text_body = :text_body, updated_at = CURRENT_TIMESTAMP "
            "WHERE account_id = :account_id AND template_type = 'email_verification'"
        ).bindparams(
            html_body=NEW_HTML_BODY,
            text_body=NEW_TEXT_BODY,
            account_id=SYSTEM_ACCOUNT_ID
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "UPDATE email_templates "
            "SET html_body = :html_body, text_body = :text_body, updated_at = CURRENT_TIMESTAMP "
            "WHERE account_id = :account_id AND template_type = 'email_verification'"
        ).bindparams(
            html_body=OLD_HTML_BODY,
            text_body=OLD_TEXT_BODY,
            account_id=SYSTEM_ACCOUNT_ID
        )
    )
