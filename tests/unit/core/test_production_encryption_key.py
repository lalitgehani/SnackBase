"""Settings must reject the default encryption key in production."""

import pytest
from pydantic import ValidationError

from snackbase.core.config import Settings
from snackbase.infrastructure.security.encryption import DEFAULT_ENCRYPTION_KEY


def test_production_rejects_default_encryption_key():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            encryption_key=DEFAULT_ENCRYPTION_KEY,
            token_secret="a-real-token-secret-for-tests-32b",
            secret_key="a-real-secret-key-for-tests-32byte",
        )
    assert "SNACKBASE_ENCRYPTION_KEY" in str(exc_info.value)


def test_production_accepts_non_default_encryption_key():
    settings = Settings(
        environment="production",
        encryption_key="production-encryption-key-value-32",
        token_secret="a-real-token-secret-for-tests-32b",
        secret_key="a-real-secret-key-for-tests-32byte",
    )
    assert settings.has_non_default_encryption_key is True
    assert settings.is_production is True


def test_development_allows_default_encryption_key():
    settings = Settings(
        environment="development",
        encryption_key=DEFAULT_ENCRYPTION_KEY,
    )
    assert settings.has_non_default_encryption_key is False
