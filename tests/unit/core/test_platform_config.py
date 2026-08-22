"""Unit tests for platform issuer settings (F2.1)."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from snackbase.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_platform_auth_disabled_by_default():
    settings = Settings()
    assert settings.platform_auth_enabled is False
    assert settings.platform_issuer is None


def test_partial_platform_config_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        Settings(platform_issuer="https://platform.example.com")

    message = str(exc_info.value)
    assert "platform_jwks_url" in message
    assert "platform_audience" in message


def test_complete_platform_config_enables_auth():
    settings = Settings(
        platform_issuer="https://platform.example.com",
        platform_jwks_url="http://localhost:9999/jwks",
        platform_audience="snackbase-instance",
    )
    assert settings.platform_auth_enabled is True
    assert settings.platform_role_claim == "snackbase_role"


def test_platform_role_claim_overridable():
    settings = Settings(
        platform_issuer="https://platform.example.com",
        platform_jwks_url="http://localhost:9999/jwks",
        platform_audience="snackbase-instance",
        platform_role_claim="custom_role",
    )
    assert settings.platform_role_claim == "custom_role"


def test_http_jwks_rejected_in_production():
    with patch.dict(
        os.environ,
        {
            "SNACKBASE_ENVIRONMENT": "production",
            "SNACKBASE_ENCRYPTION_KEY": "production-test-encryption-key-32b",
            "SNACKBASE_SECRET_KEY": "production-test-secret-key-32bytes",
            "SNACKBASE_TOKEN_SECRET": "production-test-token-secret-32by",
        },
    ):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                platform_issuer="https://platform.example.com",
                platform_jwks_url="http://localhost:9999/jwks",
                platform_audience="snackbase-instance",
            )
        assert "https://" in str(exc_info.value)


def test_http_jwks_allowed_in_development():
    settings = Settings(
        environment="development",
        platform_issuer="https://platform.example.com",
        platform_jwks_url="http://localhost:9999/jwks",
        platform_audience="snackbase-instance",
    )
    assert settings.platform_jwks_url == "http://localhost:9999/jwks"


def test_platform_auth_allowed_without_single_tenant_mode():
    """Platform principals are instance operators resolved into the system account,
    so platform auth is independent of instance tenancy. Multi-tenant instances must
    be able to enable it."""
    settings = Settings(
        platform_issuer="https://platform.example.com",
        platform_jwks_url="https://platform.example.com/jwks",
        platform_audience="snackbase-instance",
    )
    assert settings.platform_auth_enabled is True
    assert settings.single_tenant_mode is False
