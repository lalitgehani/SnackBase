"""Integration test for system configuration in email templates."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from snackbase.infrastructure.services.email_service import EmailService
from snackbase.infrastructure.persistence.models.email_template import EmailTemplateModel
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel


@pytest.mark.asyncio
async def test_system_variables_merged_into_template():
    """Test that system configuration variables are automatically merged into email templates."""
    # Mock repositories
    template_repo = MagicMock()
    log_repo = MagicMock()
    config_repo = MagicMock()
    
    # Create email service
    email_service = EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=config_repo,
    )
    
    # Mock template with system variables
    mock_template = EmailTemplateModel(
        id="test-template-id",
        account_id="test-account-id",
        template_type="email_verification",
        locale="en",
        subject="Welcome to {{ app_name }}",
        html_body="<p>Visit us at {{ app_url }}</p><p>Contact: {{ support_email }}</p>",
        text_body="Visit us at {{ app_url }}. Contact: {{ support_email }}",
        enabled=True,
        is_builtin=False,
    )
    
    # Mock system configuration
    mock_system_config = ConfigurationModel(
        id="system-config-id",
        account_id="system",
        category="system_settings",
        provider_name="system",
        display_name="System Settings",
        config={
            "app_name": "TestApp",
            "app_url": "https://testapp.com",
            "support_email": "support@testapp.com",
        },
        enabled=True,
        is_builtin=True,
        is_system=True,
        priority=0,
    )
    
    # Setup mocks
    template_repo.get_template = AsyncMock(return_value=mock_template)
    config_repo.get_config = AsyncMock(return_value=mock_system_config)
    
    # Mock provider
    mock_provider = MagicMock()
    mock_provider.send_email = AsyncMock(return_value=True)
    mock_provider.__class__.__name__ = "MockProvider"
    
    # Mock session and log creation
    mock_session = MagicMock()
    log_repo.create = AsyncMock()
    mock_session.commit = AsyncMock()
    
    # Call send_template_email with user variables
    user_variables = {
        "verification_url": "https://testapp.com/verify/abc123",
        "user_name": "John Doe",
    }
    
    result = await email_service.send_template_email(
        session=mock_session,
        to="test@example.com",
        template_type="email_verification",
        variables=user_variables,
        provider=mock_provider,
        from_email="noreply@testapp.com",
        from_name="TestApp",
        account_id="test-account-id",
        locale="en",
    )
    
    # Verify system config was fetched
    assert config_repo.get_config.called
    
    # Verify email was sent
    assert result is True
    assert mock_provider.send_email.called
    
    # Get the actual call arguments
    call_args = mock_provider.send_email.call_args
    
    # Verify subject contains system variable
    assert "TestApp" in call_args.kwargs["subject"]
    
    # Verify HTML body contains system variables
    html_body = call_args.kwargs["html_body"]
    assert "https://testapp.com" in html_body
    assert "support@testapp.com" in html_body
    
    # Verify text body contains system variables
    text_body = call_args.kwargs["text_body"]
    assert "https://testapp.com" in text_body
    assert "support@testapp.com" in text_body
    
    print("✅ System variables successfully merged into email template!")
    print(f"Subject: {call_args.kwargs['subject']}")
    print(f"HTML Body contains app_url: {'https://testapp.com' in html_body}")
    print(f"HTML Body contains support_email: {'support@testapp.com' in html_body}")


@pytest.mark.asyncio
async def test_user_variables_override_system_variables():
    """Test that user-provided variables override system configuration variables."""
    # Mock repositories
    template_repo = MagicMock()
    log_repo = MagicMock()
    config_repo = MagicMock()
    
    # Create email service
    email_service = EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=config_repo,
    )
    
    # Mock template
    mock_template = EmailTemplateModel(
        id="test-template-id",
        account_id="test-account-id",
        template_type="custom",
        locale="en",
        subject="{{ app_name }} - Custom Email",
        html_body="<p>{{ app_name }}</p>",
        text_body="{{ app_name }}",
        enabled=True,
        is_builtin=False,
    )
    
    # Mock system configuration
    mock_system_config = ConfigurationModel(
        id="system-config-id",
        account_id="system",
        category="system_settings",
        provider_name="system",
        display_name="System Settings",
        config={
            "app_name": "SystemAppName",
            "app_url": "https://system.com",
            "support_email": "system@example.com",
        },
        enabled=True,
        is_builtin=True,
        is_system=True,
        priority=0,
    )
    
    # Setup mocks
    template_repo.get_template = AsyncMock(return_value=mock_template)
    config_repo.get_config = AsyncMock(return_value=mock_system_config)
    
    # Mock provider
    mock_provider = MagicMock()
    mock_provider.send_email = AsyncMock(return_value=True)
    mock_provider.__class__.__name__ = "MockProvider"
    
    # Mock session
    mock_session = MagicMock()
    log_repo.create = AsyncMock()
    mock_session.commit = AsyncMock()
    
    # User provides their own app_name (should override system)
    user_variables = {
        "app_name": "CustomAppName",
    }
    
    result = await email_service.send_template_email(
        session=mock_session,
        to="test@example.com",
        template_type="custom",
        variables=user_variables,
        provider=mock_provider,
        from_email="noreply@test.com",
        from_name="Test",
        account_id="test-account-id",
        locale="en",
    )
    
    # Verify email was sent
    assert result is True
    
    # Get the actual call arguments
    call_args = mock_provider.send_email.call_args
    
    # Verify user variable overrode system variable
    assert "CustomAppName" in call_args.kwargs["subject"]
    assert "SystemAppName" not in call_args.kwargs["subject"]
    
    print("✅ User variables correctly override system variables!")
    print(f"Subject: {call_args.kwargs['subject']}")
