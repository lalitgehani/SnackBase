"""Integration test for email provider selection logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from snackbase.infrastructure.services.email_service import EmailService
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel

@pytest.mark.asyncio
async def test_select_provider_prefers_default():
    """Test that EmailService prefers the provider marked is_default when multiple are enabled."""
    # Mock repositories
    template_repo = MagicMock()
    log_repo = MagicMock()
    config_repo = MagicMock()
    encryption_service = MagicMock()
    encryption_service.decrypt_dict = MagicMock(side_effect=lambda x: x)  # Pass-through
    
    # Create email service
    email_service = EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=config_repo,
        encryption_service=encryption_service,
    )
    
    # Create two enabled providers, one is default
    provider1 = ConfigurationModel(
        id="p1",
        account_id="acc1",
        category="email_providers",
        provider_name="smtp",
        display_name="SMTP 1",
        config={"from_email": "p1@test.com"},
        enabled=True,
        is_default=False,
        priority=0
    )
    provider2 = ConfigurationModel(
        id="p2",
        account_id="acc1",
        category="email_providers",
        provider_name="aws_ses",
        display_name="SES 2",
        config={"from_email": "p2@test.com"},
        enabled=True,
        is_default=True,
        priority=1 # Higher priority value (lower logical priority) but marked default
    )
    
    # Mock list_configs to return both
    config_repo.list_configs = AsyncMock(return_value=[provider1, provider2])
    
    # Mock provider creation
    mock_provider = MagicMock()
    mock_provider.__class__.__name__ = "AWSESProvider"
    email_service._create_provider = MagicMock(return_value=mock_provider)
    
    # Call _get_provider (internal method that does selection)
    # We use a dummy session as it's not used in selection logic
    mock_session = MagicMock()
    provider, from_email, _, _ = await email_service._get_provider(mock_session, "acc1")
    
    # Verify provider 2 (the default one) was selected
    assert from_email == "p2@test.com"
    email_service._create_provider.assert_called_with("aws_ses", provider2.config)

@pytest.mark.asyncio
async def test_select_provider_falls_back_to_priority():
    """Test that EmailService falls back to priority if no default is marked."""
    template_repo = MagicMock()
    log_repo = MagicMock()
    config_repo = MagicMock()
    encryption_service = MagicMock()
    encryption_service.decrypt_dict = MagicMock(side_effect=lambda x: x)
    
    email_service = EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=config_repo,
        encryption_service=encryption_service,
    )
    
    # Two enabled providers, none is default
    provider1 = ConfigurationModel(
        id="p1",
        account_id="acc1",
        category="email_providers",
        provider_name="smtp",
        display_name="SMTP 1",
        config={"from_email": "p1@test.com"},
        enabled=True,
        is_default=False,
        priority=10
    )
    provider2 = ConfigurationModel(
        id="p2",
        account_id="acc1",
        category="email_providers",
        provider_name="aws_ses",
        display_name="SES 2",
        config={"from_email": "p2@test.com"},
        enabled=True,
        is_default=False,
        priority=5 # Higher priority (lower value)
    )
    
    # Mock list_configs to return both, sorted by selection logic (which is done in SQL Usually)
    # Actually email_service.py:192 just takes account_configs[0] if no default
    config_repo.list_configs = AsyncMock(return_value=[provider2, provider1])
    
    # Mock provider creation
    mock_provider = MagicMock()
    mock_provider.__class__.__name__ = "AWSESProvider"
    email_service._create_provider = MagicMock(return_value=mock_provider)
    
    mock_session = MagicMock()
    provider, from_email, _, _ = await email_service._get_provider(mock_session, "acc1")
    
    # Verify provider 2 (the first in the list) was selected
    assert from_email == "p2@test.com"
    email_service._create_provider.assert_called_with("aws_ses", provider2.config)
