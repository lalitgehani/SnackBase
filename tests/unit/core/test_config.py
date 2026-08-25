
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from snackbase.core.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings load with correct defaults."""
    # Reset cache before test
    get_settings.cache_clear()

    settings = Settings()

    assert settings.app_name == "SnackBase"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.is_testing is False


def test_settings_env_override():
    """Test that environment variables override defaults."""
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "SNACKBASE_APP_NAME": "TestApp",
        "SNACKBASE_ENVIRONMENT": "production",
        "SNACKBASE_DEBUG": "true",
        "SNACKBASE_PORT": "9000",
        # Production requires non-default encryption and signing secrets
        "SNACKBASE_ENCRYPTION_KEY": "production-test-encryption-key-32b",
        "SNACKBASE_SECRET_KEY": "production-test-secret-key-32bytes",
        "SNACKBASE_TOKEN_SECRET": "production-test-token-secret-32by",
    }):
        settings = Settings()

        assert settings.app_name == "TestApp"
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.port == 9000
        assert settings.is_production is True
        assert settings.is_development is False


def test_cors_origins_parsing():
    """Test CORS origins parsing from string."""
    get_settings.cache_clear()

    # Test valid JSON string list (standard pydantic-settings behavior)
    with patch.dict(os.environ, {
        "SNACKBASE_CORS_ORIGINS": '["http://example.com", "http://test.com"]'
    }):
        settings = Settings()
        assert "http://example.com" in settings.cors_origins
        assert "http://test.com" in settings.cors_origins
        assert len(settings.cors_origins) == 2

    # Test CSV string via direct instantiation (verifies the validator logic)
    settings = Settings(cors_origins="http://example.com,http://test.com")
    assert "http://example.com" in settings.cors_origins
    assert "http://test.com" in settings.cors_origins
    assert len(settings.cors_origins) == 2

    # Test single value via JSON
    with patch.dict(os.environ, {
        "SNACKBASE_CORS_ORIGINS": '["http://single.com"]'
    }):
        settings = Settings()
        assert settings.cors_origins == ["http://single.com"]


def test_list_settings_accept_csv_via_env():
    """Deployment tools (e.g. Dokploy) often forward CSV values via env.

    Pydantic Settings natively JSON-decodes complex fields at the source level,
    which crashes on non-JSON values. The lenient settings sources must accept
    plain comma-separated strings for every list field.
    """
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "SNACKBASE_CORS_ORIGINS": "https://app.example.com, https://admin.example.com",
        "SNACKBASE_CORS_ALLOW_METHODS": "GET,POST",
        "SNACKBASE_CORS_ALLOW_HEADERS": "*,Authorization",
        "SNACKBASE_ALLOWED_MIME_TYPES": "image/png,application/pdf",
    }):
        settings = Settings()
        assert settings.cors_origins == ["https://app.example.com", "https://admin.example.com"]
        assert settings.cors_allow_methods == ["GET", "POST"]
        assert settings.cors_allow_headers == ["*", "Authorization"]
        assert settings.allowed_mime_types == ["image/png", "application/pdf"]


def test_secret_key_validation():
    """Test secret key validation logic."""
    # Default insecure key is allowed but logged (implied)
    settings = Settings()
    assert settings.secret_key == "change-me-in-production-use-openssl-rand-hex-32"

    # Custom key works
    with patch.dict(os.environ, {"SNACKBASE_SECRET_KEY": "secure-key"}):
        settings = Settings()
        assert settings.secret_key == "secure-key"


def test_database_url_sync():
    """Test synchronous database URL generation."""
    # SQLite
    settings = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert settings.database_url_sync == "sqlite:///./test.db"

    # PostgreSQL
    settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")
    assert settings.database_url_sync == "postgresql://user:pass@localhost/db"


def test_rate_limit_burst_multiplier_default():
    """The burst ceiling is a multiple of the per-minute allowance, defaulting to 1.0."""
    settings = Settings()
    assert settings.rate_limit_burst_multiplier == 1.0
    assert not hasattr(settings, "rate_limit_burst")


def test_rate_limit_burst_multiplier_parsed_as_float_from_env():
    with patch.dict(os.environ, {"SNACKBASE_RATE_LIMIT_BURST_MULTIPLIER": "2.5"}):
        settings = Settings()
        assert settings.rate_limit_burst_multiplier == 2.5


def test_trusted_proxies_accepts_cidr_and_wildcard_from_env():
    with patch.dict(os.environ, {"SNACKBASE_TRUSTED_PROXIES": "10.0.0.0/8,*"}):
        settings = Settings()
        assert settings.trusted_proxies == ["10.0.0.0/8", "*"]
        assert settings.trusted_proxy_matcher.trust_any is True
        assert settings.trusted_proxy_matcher.matches("198.51.100.4") is True


def test_trusted_proxies_rejects_an_unparseable_entry_at_startup():
    with patch.dict(os.environ, {"SNACKBASE_TRUSTED_PROXIES": "127.0.0.1,not-an-ip"}):
        with pytest.raises(ValidationError, match="not-an-ip"):
            Settings()
