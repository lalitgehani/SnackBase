"""Unit tests for email provider selection logic."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from snackbase.infrastructure.security.encryption import EncryptionService
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.persistence.repositories.email_log_repository import (
    EmailLogRepository,
)
from snackbase.infrastructure.persistence.repositories.email_template_repository import (
    EmailTemplateRepository,
)
from snackbase.infrastructure.services.email.smtp_provider import SMTPProvider
from snackbase.infrastructure.services.email.aws_ses_provider import AWSESProvider
from snackbase.infrastructure.services.email.resend_provider import ResendProvider
from snackbase.infrastructure.services.email_service import EmailService, SYSTEM_ACCOUNT_ID


@pytest.fixture
def mock_encryption_service():
    """Create a mock encryption service."""
    service = MagicMock(spec=EncryptionService)
    service.decrypt_dict = MagicMock(side_effect=lambda x: x)  # Pass-through
    return service


@pytest.fixture
def mock_config_repository():
    """Create a mock configuration repository."""
    return MagicMock(spec=ConfigurationRepository)


@pytest.fixture
def email_service(mock_encryption_service, mock_config_repository):
    """Create an email service instance for testing."""
    template_repo = MagicMock(spec=EmailTemplateRepository)
    log_repo = MagicMock(spec=EmailLogRepository)
    
    return EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=mock_config_repository,
        encryption_service=mock_encryption_service,
    )


@pytest.mark.asyncio
async def test_select_provider_with_account_config(email_service, mock_config_repository):
    """Test that account-specific provider is selected when available."""
    # Setup mock config
    account_id = "test-account-123"
    mock_config = MagicMock()
    mock_config.provider_name = "smtp"
    mock_config.is_system = False
    mock_config.config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user",
        "password": "pass",
        "use_tls": True,
        "from_email": "test@example.com",
        "from_name": "Test",
    }
    
    mock_config_repository.list_configs = AsyncMock(return_value=[mock_config])
    mock_session = AsyncMock()
    
    # Execute
    provider, from_email, from_name, reply_to = await email_service._select_provider(
        mock_session, account_id
    )
    
    # Verify
    assert isinstance(provider, SMTPProvider)
    assert from_email == "test@example.com"
    assert from_name == "Test"
    
    # Verify it checked account-specific config first
    mock_config_repository.list_configs.assert_called_once_with(
        category="email_providers",
        account_id=account_id,
        is_system=False,
        enabled_only=True,
    )


@pytest.mark.asyncio
async def test_select_provider_fallback_to_system(email_service, mock_config_repository):
    """Test fallback to system-level provider when no account config exists."""
    account_id = "test-account-123"
    
    # Setup mock: no account config, but system config exists
    system_config = MagicMock()
    system_config.provider_name = "aws_ses"
    system_config.is_system = True
    system_config.config = {
        "region": "us-east-1",
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "from_email": "system@example.com",
        "from_name": "System",
    }
    
    # First call returns empty (no account config), second returns system config
    mock_config_repository.list_configs = AsyncMock(side_effect=[[], [system_config]])
    mock_session = AsyncMock()
    
    # Execute
    provider, from_email, from_name, reply_to = await email_service._select_provider(
        mock_session, account_id
    )
    
    # Verify
    assert isinstance(provider, AWSESProvider)
    assert from_email == "system@example.com"
    assert from_name == "System"
    
    # Verify it tried account config first, then system
    assert mock_config_repository.list_configs.call_count == 2
    calls = mock_config_repository.list_configs.call_args_list
    
    # First call: account-specific
    assert calls[0][1]["account_id"] == account_id
    assert calls[0][1]["is_system"] is False
    
    # Second call: system-level
    assert calls[1][1]["account_id"] == SYSTEM_ACCOUNT_ID
    assert calls[1][1]["is_system"] is True


@pytest.mark.asyncio
async def test_select_provider_no_enabled_provider(email_service, mock_config_repository):
    """Test error when no enabled provider is found."""
    account_id = "test-account-123"
    
    # Setup mock: no configs at all
    mock_config_repository.list_configs = AsyncMock(return_value=[])
    mock_session = AsyncMock()
    
    # Execute and verify exception
    with pytest.raises(ValueError) as exc_info:
        await email_service._select_provider(mock_session, account_id)
    
    assert "No enabled email provider configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_select_provider_only_enabled(email_service, mock_config_repository):
    """Test that only enabled providers are considered."""
    account_id = "test-account-123"
    
    # This is implicitly tested by the enabled_only=True parameter
    # Just verify the parameter is passed correctly
    mock_config_repository.list_configs = AsyncMock(return_value=[])
    mock_session = AsyncMock()
    
    try:
        await email_service._select_provider(mock_session, account_id)
    except ValueError:
        pass  # Expected
    
    # Verify enabled_only was passed
    calls = mock_config_repository.list_configs.call_args_list
    for call in calls:
        assert call[1]["enabled_only"] is True


@pytest.mark.asyncio
async def test_provider_cache_hit(email_service, mock_config_repository):
    """Test that cached provider is returned on subsequent calls."""
    account_id = "test-account-123"
    
    mock_config = MagicMock()
    mock_config.provider_name = "resend"
    mock_config.is_system = False
    mock_config.config = {
        "api_key": "re_123456",
        "from_email": "test@example.com",
        "from_name": "Test",
    }
    
    mock_config_repository.list_configs = AsyncMock(return_value=[mock_config])
    mock_session = AsyncMock()
    
    # First call - should query database
    provider1, _, _, _ = await email_service._get_provider(mock_session, account_id)
    
    # Second call - should use cache
    provider2, _, _, _ = await email_service._get_provider(mock_session, account_id)
    
    # Verify same provider instance is returned (from cache)
    assert provider1 is provider2
    
    # Verify database was only queried once
    assert mock_config_repository.list_configs.call_count == 1


@pytest.mark.asyncio
async def test_provider_cache_ttl_expiry(email_service, mock_config_repository):
    """Test that cache expires after TTL."""
    account_id = "test-account-123"
    
    mock_config = MagicMock()
    mock_config.provider_name = "smtp"
    mock_config.is_system = False
    mock_config.config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user",
        "password": "pass",
        "use_tls": True,
        "from_email": "test@example.com",
        "from_name": "Test",
    }
    
    mock_config_repository.list_configs = AsyncMock(return_value=[mock_config])
    mock_session = AsyncMock()
    
    # First call
    await email_service._get_provider(mock_session, account_id)
    
    # Manually expire the cache by manipulating the timestamp
    cache_key = f"provider:{account_id}"
    if cache_key in email_service._provider_cache._cache:
        provider, _ = email_service._provider_cache._cache[cache_key]
        # Set timestamp to 6 minutes ago (beyond 5-minute TTL)
        email_service._provider_cache._cache[cache_key] = (
            provider,
            datetime.now(UTC) - timedelta(seconds=360)
        )
    
    # Second call - should query database again
    await email_service._get_provider(mock_session, account_id)
    
    # Verify database was queried twice
    assert mock_config_repository.list_configs.call_count == 2


@pytest.mark.asyncio
async def test_provider_cache_invalidation(email_service, mock_config_repository):
    """Test that cache can be invalidated."""
    account_id = "test-account-123"
    
    mock_config = MagicMock()
    mock_config.provider_name = "smtp"
    mock_config.is_system = False
    mock_config.config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user",
        "password": "pass",
        "use_tls": True,
        "from_email": "test@example.com",
        "from_name": "Test",
    }
    
    mock_config_repository.list_configs = AsyncMock(return_value=[mock_config])
    mock_session = AsyncMock()
    
    # First call - populate cache
    await email_service._get_provider(mock_session, account_id)
    
    # Invalidate cache
    email_service.invalidate_provider_cache(account_id)
    
    # Second call - should query database again
    await email_service._get_provider(mock_session, account_id)
    
    # Verify database was queried twice
    assert mock_config_repository.list_configs.call_count == 2


@pytest.mark.asyncio
async def test_provider_factory_creates_correct_providers(email_service):
    """Test that provider factory creates the correct provider types."""
    # Test SMTP
    smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user",
        "password": "pass",
        "use_tls": True,
        "from_email": "test@example.com",
    }
    smtp_provider = email_service._create_provider("smtp", smtp_config)
    assert isinstance(smtp_provider, SMTPProvider)
    
    # Test AWS SES
    ses_config = {
        "region": "us-east-1",
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "from_email": "test@example.com",
    }
    ses_provider = email_service._create_provider("aws_ses", ses_config)
    assert isinstance(ses_provider, AWSESProvider)
    
    # Test Resend
    resend_config = {
        "api_key": "re_123456",
        "from_email": "test@example.com",
    }
    resend_provider = email_service._create_provider("resend", resend_config)
    assert isinstance(resend_provider, ResendProvider)
    
    # Test unknown provider
    with pytest.raises(ValueError) as exc_info:
        email_service._create_provider("unknown", {})
    assert "Unknown email provider" in str(exc_info.value)
