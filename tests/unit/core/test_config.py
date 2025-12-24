
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
        "SNACKBASE_PORT": "9000"
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
