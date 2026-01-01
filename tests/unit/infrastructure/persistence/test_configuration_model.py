"""Unit tests for ConfigurationModel."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    ConfigurationModel,
    OAuthStateModel,
)


@pytest.mark.asyncio
async def test_configuration_model_instantiation():
    """Test that ConfigurationModel can be instantiated with all fields."""
    config_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())

    config = ConfigurationModel(
        id=config_id,
        account_id=account_id,
        category="auth_providers",
        provider_name="google",
        display_name="Google OAuth",
        logo_url="/assets/providers/google.svg",
        config_schema={"type": "object", "properties": {"client_id": {"type": "string"}}},
        config={"client_id": "test_client_id", "client_secret": "encrypted_secret"},
        enabled=True,
        is_builtin=False,
        is_system=False,
        priority=10,
    )

    assert config.id == config_id
    assert config.account_id == account_id
    assert config.category == "auth_providers"
    assert config.provider_name == "google"
    assert config.display_name == "Google OAuth"
    assert config.logo_url == "/assets/providers/google.svg"
    assert config.config_schema == {
        "type": "object",
        "properties": {"client_id": {"type": "string"}},
    }
    assert config.config == {"client_id": "test_client_id", "client_secret": "encrypted_secret"}
    assert config.enabled is True
    assert config.is_builtin is False
    assert config.is_system is False
    assert config.priority == 10


@pytest.mark.asyncio
async def test_configuration_model_defaults():
    """Test that ConfigurationModel can be instantiated without optional fields."""
    config_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())

    config = ConfigurationModel(
        id=config_id,
        account_id=account_id,
        category="email_providers",
        provider_name="ses",
        display_name="Amazon SES",
        config={"region": "us-east-1"},
    )

    # These fields are optional and should be None if not provided
    assert config.logo_url is None  # nullable
    assert config.config_schema is None  # nullable

    # Note: Server defaults (enabled, is_builtin, is_system, priority) only apply
    # after the model is persisted to the database, so we don't test them here



@pytest.mark.asyncio
async def test_configuration_model_json_columns():
    """Test that JSON columns work correctly."""
    config_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())

    # Test with complex nested JSON
    complex_config = {
        "client_id": "test_id",
        "client_secret": "encrypted_secret",
        "scopes": ["openid", "email", "profile"],
        "metadata": {"tenant_id": "common", "region": "us"},
    }

    complex_schema = {
        "type": "object",
        "required": ["client_id", "client_secret"],
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "scopes": {"type": "array", "items": {"type": "string"}},
        },
    }

    config = ConfigurationModel(
        id=config_id,
        account_id=account_id,
        category="auth_providers",
        provider_name="microsoft",
        display_name="Microsoft Azure AD",
        config=complex_config,
        config_schema=complex_schema,
    )

    assert config.config == complex_config
    assert config.config_schema == complex_schema
    assert config.config["scopes"] == ["openid", "email", "profile"]
    assert config.config["metadata"]["tenant_id"] == "common"


@pytest.mark.asyncio
async def test_configuration_model_repr():
    """Test that __repr__ returns expected format."""
    config_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())

    config = ConfigurationModel(
        id=config_id,
        account_id=account_id,
        category="storage_providers",
        provider_name="s3",
        display_name="Amazon S3",
        config={"bucket": "test-bucket"},
    )

    repr_str = repr(config)
    assert "Configuration" in repr_str
    assert config_id in repr_str
    assert "storage_providers" in repr_str
    assert "s3" in repr_str
    assert account_id in repr_str


@pytest.mark.asyncio
async def test_oauth_state_model_instantiation():
    """Test that OAuthStateModel can be instantiated with all fields."""
    state_id = str(uuid.uuid4())
    token = "secure_token_abc123"
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    state = OAuthStateModel(
        id=state_id,
        provider_name="github",
        state_token=token,
        redirect_uri="https://app.snackbase.com/callback",
        code_verifier="pkce_verifier_xyz",
        metadata_={"step": "authorize", "source": "mobile"},
        expires_at=expires,
    )

    assert state.id == state_id
    assert state.provider_name == "github"
    assert state.state_token == token
    assert state.redirect_uri == "https://app.snackbase.com/callback"
    assert state.code_verifier == "pkce_verifier_xyz"
    assert state.metadata_ == {"step": "authorize", "source": "mobile"}
    assert state.expires_at == expires


@pytest.mark.asyncio
async def test_oauth_state_model_expiration():
    """Test the is_expired property of OAuthStateModel."""
    # Not expired
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    state = OAuthStateModel(
        id=str(uuid.uuid4()),
        provider_name="google",
        state_token="token1",
        redirect_uri="uri",
        expires_at=future,
    )
    assert state.is_expired is False

    # Expired
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    state_expired = OAuthStateModel(
        id=str(uuid.uuid4()),
        provider_name="google",
        state_token="token2",
        redirect_uri="uri",
        expires_at=past,
    )
    assert state_expired.is_expired is True


@pytest.mark.asyncio
async def test_oauth_state_model_repr():
    """Test that __repr__ returns expected format for OAuthStateModel."""
    state_id = str(uuid.uuid4())
    token = "very_long_secure_token_value"
    state = OAuthStateModel(
        id=state_id,
        provider_name="apple",
        state_token=token,
        redirect_uri="uri",
        expires_at=datetime.now(timezone.utc),
    )

    repr_str = repr(state)
    assert "OAuthState" in repr_str
    assert state_id in repr_str
    assert "apple" in repr_str
    assert token[:8] in repr_str
