"""CFG-KEY-*: production signing-secret validation (C-03).

``Settings.validate_secret_key`` is a no-op: it recognises the shipped default
and then deliberately falls through with ``pass``. There is no validator for
``token_secret`` at all. So a production deployment that never sets either
variable boots happily and signs every JWT and API key with a value published
in the repository, `.env.example` and the Docker docs.

The encryption key already fails closed
(``validate_production_encryption_key``); these tests assert the two signing
secrets behave the same way. Mirrors
``tests/unit/core/test_production_encryption_key.py``.
"""

import pytest
from pydantic import ValidationError

from snackbase.core.config import Settings

DEFAULT_SIGNING_SECRET = "change-me-in-production-use-openssl-rand-hex-32"

VALID_SECRET_KEY = "a-real-secret-key-for-tests-32byte"
VALID_TOKEN_SECRET = "a-real-token-secret-for-tests-32b"
VALID_ENCRYPTION_KEY = "production-encryption-key-value-32"


@pytest.mark.parametrize(
    ("key_name", "env_var"),
    [
        ("secret_key", "SNACKBASE_SECRET_KEY"),
        ("token_secret", "SNACKBASE_TOKEN_SECRET"),
    ],
)
def test_cfg_key_001_production_rejects_default_signing_secret(
    key_name: str, env_var: str
) -> None:
    """CFG-KEY-001: production must refuse to boot on a default signing secret."""
    kwargs = {
        "environment": "production",
        "secret_key": VALID_SECRET_KEY,
        "token_secret": VALID_TOKEN_SECRET,
        "encryption_key": VALID_ENCRYPTION_KEY,
    }
    kwargs[key_name] = DEFAULT_SIGNING_SECRET

    with pytest.raises(ValidationError) as exc_info:
        Settings(**kwargs)

    assert env_var in str(exc_info.value)


def test_cfg_key_002_production_accepts_non_default_signing_secrets() -> None:
    """CFG-KEY-002: negative control — real secrets construct without error."""
    settings = Settings(
        environment="production",
        secret_key=VALID_SECRET_KEY,
        token_secret=VALID_TOKEN_SECRET,
        encryption_key=VALID_ENCRYPTION_KEY,
    )

    assert settings.is_production is True
    assert settings.secret_key == VALID_SECRET_KEY
    assert settings.token_secret == VALID_TOKEN_SECRET


def test_cfg_key_003_development_allows_default_signing_secrets() -> None:
    """CFG-KEY-003: local development keeps working with the shipped defaults."""
    settings = Settings(
        environment="development",
        secret_key=DEFAULT_SIGNING_SECRET,
        token_secret=DEFAULT_SIGNING_SECRET,
    )

    assert settings.is_development is True
    assert settings.secret_key == DEFAULT_SIGNING_SECRET


def test_cfg_key_004_production_still_rejects_default_encryption_key() -> None:
    """CFG-KEY-004: regression — the existing encryption-key guard is unchanged."""
    from snackbase.infrastructure.security.encryption import DEFAULT_ENCRYPTION_KEY

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            secret_key=VALID_SECRET_KEY,
            token_secret=VALID_TOKEN_SECRET,
            encryption_key=DEFAULT_ENCRYPTION_KEY,
        )

    assert "SNACKBASE_ENCRYPTION_KEY" in str(exc_info.value)
