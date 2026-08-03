"""Unit tests for schema-declared configuration secret encryption."""

from snackbase.core.configuration.config_registry import ConfigurationRegistry
from snackbase.infrastructure.security.encryption import (
    EncryptionService,
    extract_secret_paths_from_schema,
)


def test_extract_and_encrypt_only_secret_paths():
    schema = {
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string", "secret": True},
            "password": {"type": "string", "secret": True},
        },
    }
    paths = extract_secret_paths_from_schema(schema)
    assert set(paths) == {"client_secret", "password"}

    reg = ConfigurationRegistry(EncryptionService("test-key"))
    config = {
        "client_id": "public-id",
        "client_secret": "sekrit",
        "password": "pw",
    }
    encrypted = reg._encrypt_config(config, schema)
    assert encrypted["client_id"] == "public-id"
    assert encrypted["client_secret"] != "sekrit"
    assert encrypted["password"] != "pw"

    decrypted = reg._decrypt_config(encrypted, schema)
    assert decrypted == config


def test_fallback_to_heuristics_without_schema():
    reg = ConfigurationRegistry(EncryptionService("test-key"))
    config = {"api_key": "k", "name": "n"}
    encrypted = reg._encrypt_config(config, None)
    assert encrypted["name"] == "n"
    assert encrypted["api_key"] != "k"
    assert reg._decrypt_config(encrypted, None) == config
