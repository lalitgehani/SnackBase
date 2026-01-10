"""enhance password reset template

Revision ID: 038a7194dd07
Revises: bb38e4d658cd
Create Date: 2026-01-10 18:05:52.469527

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '038a7194dd07'
down_revision: str | Sequence[str] | None = 'bb38e4d658cd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


import sqlalchemy as sa
from alembic import op

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

NEW_SUBJECT = "Reset your {{ app_name }} password"
NEW_HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
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
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Reset Your Password</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. Click the button below to create a new password:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ reset_url }}" class="button" style="display: inline-block; background-color: #e74c3c; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(231,76,60,0.3);">Reset Password</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #e74c3c; font-size: 14px;">{{ reset_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #fef5f5; padding: 16px; border-radius: 6px; border-left: 4px solid #e74c3c;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Reset Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This password reset link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Security Warning -->
                    <tr>
                        <td style="padding-top: 20px;">
                            <div style="background-color: #fff5f5; border-left: 4px solid #fc8181; padding: 16px; border-radius: 6px;">
                                <p style="margin: 0 0 8px 0; color: #c53030; font-size: 14px; font-weight: 600;">🔒 Security Notice</p>
                                <p style="margin: 0; color: #742a2a; font-size: 13px; line-height: 1.5;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged.{% if ip_address %} This request was initiated from IP address: <strong>{{ ip_address }}</strong>.{% endif %} For security, we recommend changing your password if you suspect unauthorized access to your account.</p>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">This password reset was requested from your {{ app_name }} account.</p>
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
{{ app_name }} - Reset Your Password

Hello{% if user_name %} {{ user_name }}{% endif %},

We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. To create a new password, visit the following link:

{{ reset_url }}

{% if token %}Reset Code: {{ token }}{% endif %}

{% if expires_at %}This password reset link will expire on {{ expires_at }}.{% endif %}

SECURITY NOTICE:
If you didn't request a password reset, please ignore this email. Your password will remain unchanged.{% if ip_address %} This request was initiated from IP address: {{ ip_address }}.{% endif %} For security, we recommend changing your password if you suspect unauthorized access to your account.

This password reset was requested from your {{ app_name }} account.

Need help? Visit {{ app_url }}
""".strip()

OLD_SUBJECT = "Reset your password for {{ app_name }}"
OLD_HTML_BODY = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
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
                            <h2 style="margin: 0 0 20px 0; color: #2c3e50; font-size: 24px; font-weight: 600;">Reset Your Password</h2>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">Hello{% if user_name %} {{ user_name }}{% endif %},</p>
                            <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 16px; line-height: 1.6;">We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. Click the button below to create a new password:</p>
                        </td>
                    </tr>
                    <!-- Button -->
                    <tr>
                        <td style="text-align: center; padding: 30px 0;">
                            <a href="{{ reset_url }}" class="button" style="display: inline-block; background-color: #e74c3c; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(231,76,60,0.3);">Reset Password</a>
                        </td>
                    </tr>
                    <!-- Alternative Link -->
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px 0; color: #718096; font-size: 14px;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; word-break: break-all; color: #e74c3c; font-size: 14px;">{{ reset_url }}</p>
                        </td>
                    </tr>
                    <!-- Token Info -->
                    {% if token %}
                    <tr>
                        <td style="background-color: #fef5f5; padding: 16px; border-radius: 6px; border-left: 4px solid #e74c3c;">
                            <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">Reset Code:</p>
                            <p style="margin: 0; color: #2d3748; font-size: 16px; font-family: 'Courier New', monospace; letter-spacing: 2px;">{{ token }}</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Expiration -->
                    {% if expires_at %}
                    <tr>
                        <td style="padding-top: 20px;">
                            <p style="margin: 0; color: #718096; font-size: 14px;">⏰ This password reset link will expire on {{ expires_at }}.</p>
                        </td>
                    </tr>
                    {% endif %}
                    <!-- Security Warning -->
                    <tr>
                        <td style="padding-top: 20px;">
                            <div style="background-color: #fff5f5; border-left: 4px solid #fc8181; padding: 16px; border-radius: 6px;">
                                <p style="margin: 0 0 8px 0; color: #c53030; font-size: 14px; font-weight: 600;">🔒 Security Notice</p>
                                <p style="margin: 0; color: #742a2a; font-size: 13px; line-height: 1.5;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged. For security, we recommend changing your password if you suspect unauthorized access to your account.</p>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 30px; border-top: 1px solid #e2e8f0; margin-top: 30px;">
                            <p style="margin: 0 0 8px 0; color: #a0aec0; font-size: 13px; line-height: 1.5;">This password reset was requested from your {{ app_name }} account.</p>
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
{{ app_name }} - Reset Your Password

Hello{% if user_name %} {{ user_name }}{% endif %},

We received a request to reset the password for your {{ app_name }} account{% if user_email %} ({{ user_email }}){% endif %}. To create a new password, visit the following link:

{{ reset_url }}

{% if token %}Reset Code: {{ token }}{% endif %}

{% if expires_at %}This password reset link will expire on {{ expires_at }}.{% endif %}

SECURITY NOTICE:
If you didn't request a password reset, please ignore this email. Your password will remain unchanged. For security, we recommend changing your password if you suspect unauthorized access to your account.

This password reset was requested from your {{ app_name }} account.

Need help? Visit {{ app_url }}
""".strip()


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE email_templates "
            "SET subject = :subject, html_body = :html_body, text_body = :text_body, updated_at = CURRENT_TIMESTAMP "
            "WHERE account_id = :account_id AND template_type = 'password_reset'"
        ).bindparams(
            subject=NEW_SUBJECT,
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
            "SET subject = :subject, html_body = :html_body, text_body = :text_body, updated_at = CURRENT_TIMESTAMP "
            "WHERE account_id = :account_id AND template_type = 'password_reset'"
        ).bindparams(
            subject=OLD_SUBJECT,
            html_body=OLD_HTML_BODY,
            text_body=OLD_TEXT_BODY,
            account_id=SYSTEM_ACCOUNT_ID
        )
    )
