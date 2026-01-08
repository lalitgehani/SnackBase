"""Unit tests for email template rendering functionality.

Tests verify that email templates are correctly rendered with Jinja2 variable
substitution and that the rendered output is valid.
"""

import pytest

from snackbase.infrastructure.services.email.template_renderer import (
    get_template_renderer,
)


@pytest.fixture
def renderer():
    """Fixture to get template renderer instance."""
    return get_template_renderer()


def test_render_simple_variable(renderer) -> None:
    """Test rendering a simple variable substitution."""
    template = "Hello {{ name }}!"
    variables = {"name": "World"}
    result = renderer.render(template, variables)
    assert result == "Hello World!"


def test_render_email_verification_template(renderer) -> None:
    """Test rendering email verification template with all variables."""
    template = """
    <h1>{{ app_name }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>Verify your email: {{ verification_url }}</p>
    <p>Token: {{ token }}</p>
    <p>Expires: {{ expires_at }}</p>
    """
    variables = {
        "app_name": "SnackBase",
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "verification_url": "https://example.com/verify?token=abc123",
        "token": "abc123",
        "expires_at": "2026-01-09 20:00:00",
    }
    result = renderer.render(template, variables)

    assert "SnackBase" in result
    assert "John Doe" in result
    assert "https://example.com/verify?token=abc123" in result
    assert "abc123" in result
    assert "2026-01-09 20:00:00" in result


def test_render_password_reset_template(renderer) -> None:
    """Test rendering password reset template with all variables."""
    template = """
    <h1>{{ app_name }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>Reset your password: {{ reset_url }}</p>
    <p>Token: {{ token }}</p>
    <p>Expires: {{ expires_at }}</p>
    """
    variables = {
        "app_name": "SnackBase",
        "user_name": "Jane Smith",
        "user_email": "jane@example.com",
        "reset_url": "https://example.com/reset?token=xyz789",
        "token": "xyz789",
        "expires_at": "2026-01-09 21:00:00",
    }
    result = renderer.render(template, variables)

    assert "SnackBase" in result
    assert "Jane Smith" in result
    assert "https://example.com/reset?token=xyz789" in result
    assert "xyz789" in result
    assert "2026-01-09 21:00:00" in result


def test_render_invitation_template(renderer) -> None:
    """Test rendering invitation template with all variables."""
    template = """
    <h1>{{ app_name }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>{{ invited_by }} invited you to {{ account_name }}</p>
    <p>Accept: {{ invitation_url }}</p>
    <p>Token: {{ token }}</p>
    """
    variables = {
        "app_name": "SnackBase",
        "user_name": "Bob Johnson",
        "email": "bob@example.com",
        "account_name": "Acme Corp",
        "invited_by": "Alice Admin",
        "invitation_url": "https://example.com/invite?token=inv456",
        "token": "inv456",
    }
    result = renderer.render(template, variables)

    assert "SnackBase" in result
    assert "Bob Johnson" in result
    assert "Acme Corp" in result
    assert "Alice Admin" in result
    assert "https://example.com/invite?token=inv456" in result
    assert "inv456" in result


def test_template_variables_substitution(renderer) -> None:
    """Test that Jinja2 variable substitution works correctly."""
    template = "{{ var1 }} and {{ var2 }} and {{ var3 }}"
    variables = {"var1": "foo", "var2": "bar", "var3": "baz"}
    result = renderer.render(template, variables)
    assert result == "foo and bar and baz"


def test_template_conditional_rendering(renderer) -> None:
    """Test that Jinja2 conditionals work correctly."""
    template = "Hello{% if user_name %} {{ user_name }}{% endif %}!"
    
    # With user_name
    result_with_name = renderer.render(template, {"user_name": "Alice"})
    assert result_with_name == "Hello Alice!"
    
    # Without user_name
    result_without_name = renderer.render(template, {})
    assert result_without_name == "Hello!"


def test_template_missing_variable_renders_empty(renderer) -> None:
    """Test that missing variables render as empty strings."""
    template = "Hello {{ missing_var }}!"
    result = renderer.render(template, {})
    assert result == "Hello !"


def test_html_template_basic_structure(renderer) -> None:
    """Test that HTML templates maintain basic structure after rendering."""
    template = """
    <!DOCTYPE html>
    <html>
    <head><title>{{ title }}</title></head>
    <body>
        <h1>{{ heading }}</h1>
        <p>{{ content }}</p>
    </body>
    </html>
    """
    variables = {
        "title": "Test Email",
        "heading": "Welcome",
        "content": "This is a test",
    }
    result = renderer.render(template, variables)

    assert "<!DOCTYPE html>" in result
    assert "<html>" in result
    assert "<title>Test Email</title>" in result
    assert "<h1>Welcome</h1>" in result
    assert "<p>This is a test</p>" in result


def test_text_template_formatting(renderer) -> None:
    """Test that text templates maintain formatting."""
    template = """
{{ app_name }} - {{ subject }}

Hello {{ user_name }},

{{ message }}

Best regards,
The {{ app_name }} Team
    """
    variables = {
        "app_name": "SnackBase",
        "subject": "Welcome",
        "user_name": "Test User",
        "message": "Thank you for signing up!",
    }
    result = renderer.render(template, variables)

    assert "SnackBase - Welcome" in result
    assert "Hello Test User," in result
    assert "Thank you for signing up!" in result
    assert "The SnackBase Team" in result


def test_template_with_special_characters(renderer) -> None:
    """Test rendering templates with special characters."""
    template = "Email: {{ email }}, Symbol: {{ symbol }}"
    variables = {
        "email": "test@example.com",
        "symbol": "© 2026",
    }
    result = renderer.render(template, variables)

    assert "test@example.com" in result
    assert "© 2026" in result


def test_template_with_url_variables(renderer) -> None:
    """Test rendering templates with URL variables."""
    template = '<a href="{{ url }}">{{ link_text }}</a>'
    variables = {
        "url": "https://example.com/verify?token=abc&user=123",
        "link_text": "Click here",
    }
    result = renderer.render(template, variables)

    # Jinja2 auto-escapes HTML, so & becomes &amp;
    assert "https://example.com/verify?token=abc&amp;user=123" in result
    assert "Click here" in result


def test_render_multiple_same_variable(renderer) -> None:
    """Test rendering template with same variable used multiple times."""
    template = "{{ name }} said: '{{ name }} is great!' - {{ name }}"
    variables = {"name": "SnackBase"}
    result = renderer.render(template, variables)

    assert result == "SnackBase said: 'SnackBase is great!' - SnackBase"


def test_template_with_nested_conditionals(renderer) -> None:
    """Test rendering template with nested conditionals."""
    template = """
{% if user_name %}
Hello {{ user_name }}!
{% if user_email %}
Your email is {{ user_email }}.
{% endif %}
{% endif %}
    """
    variables = {
        "user_name": "Alice",
        "user_email": "alice@example.com",
    }
    result = renderer.render(template, variables)

    assert "Hello Alice!" in result
    assert "Your email is alice@example.com." in result
