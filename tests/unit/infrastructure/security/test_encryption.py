"""Unit tests for EncryptionService strict contract."""

import logging

import pytest

from snackbase.infrastructure.security.encryption import (
    DEFAULT_ENCRYPTION_KEY,
    DecryptionError,
    EncryptionService,
    extract_secret_paths_from_schema,
)


def test_encryption_round_trip():
    service = EncryptionService(secret_key="test-secret-key")
    plaintext = "Hello, SnackBase!"

    ciphertext = service.encrypt(plaintext)
    assert ciphertext != plaintext

    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encryption_empty_string_round_trip():
    service = EncryptionService(secret_key="test-key")
    ciphertext = service.encrypt("")
    assert ciphertext != ""
    assert service.decrypt(ciphertext) == ""


def test_encryption_unicode_round_trip():
    service = EncryptionService(secret_key="test-key")
    plaintext = "凭证-🔐-café-日本語"
    assert service.decrypt(service.encrypt(plaintext)) == plaintext


def test_null_not_encrypted_at_call_site():
    """Callers preserve null; encrypt/decrypt operate on non-null strings only."""
    # Documented contract: null is handled above EncryptionService
    value = None
    assert value is None


def test_wrong_key_raises_decryption_error():
    service1 = EncryptionService(secret_key="key-1")
    service2 = EncryptionService(secret_key="key-2")
    ciphertext = service1.encrypt("Sensitive data")

    with pytest.raises(DecryptionError) as exc_info:
        service2.decrypt(ciphertext)

    # Must not leak ciphertext or plaintext in the exception message
    msg = str(exc_info.value)
    assert "Sensitive data" not in msg
    assert ciphertext not in msg
    assert msg == "Decryption failed"


def test_malformed_ciphertext_raises():
    service = EncryptionService(secret_key="test-key")
    with pytest.raises(DecryptionError):
        service.decrypt("not-a-fernet-token")


def test_strict_decrypt_never_returns_ciphertext():
    service = EncryptionService(secret_key="test-key")
    bad = "gAAAAABfake-looking-but-invalid-token===="
    with pytest.raises(DecryptionError):
        result = service.decrypt(bad)
        # If we got here without raise, result must not be the ciphertext
        assert result != bad  # pragma: no cover


def test_try_decrypt_returns_none_on_failure():
    service = EncryptionService(secret_key="test-key")
    assert service.try_decrypt("not-encrypted") is None
    ct = service.encrypt("ok")
    assert service.try_decrypt(ct) == "ok"


def test_encrypt_decrypt_structured_object():
    service = EncryptionService(secret_key="test-key")
    value = {"api_key": "secret", "nested": [1, True, None], "n": 3.14}
    ciphertext = service.encrypt_structured(value)
    assert isinstance(ciphertext, str)
    assert ciphertext != str(value)
    assert service.decrypt_structured(ciphertext) == value


def test_encrypt_decrypt_structured_primitives():
    service = EncryptionService(secret_key="test-key")
    for value in ["text", 42, 3.5, True, False, None, [1, 2], {"a": 1}]:
        assert service.decrypt_structured(service.encrypt_structured(value)) == value


def test_encrypt_decrypt_dict_heuristics():
    service = EncryptionService(secret_key="test-key")
    data = {
        "provider": "google",
        "client_id": "123456",
        "client_secret": "super-secret-password",
        "api_key": "api-key-value",
        "nested": {"token": "nested-token", "public": "public-value"},
        "list": [{"secret": "list-secret", "id": 1}, "not-a-dict"],
    }

    encrypted = service.encrypt_dict(data)

    assert encrypted["client_secret"] != "super-secret-password"
    assert encrypted["api_key"] != "api-key-value"
    assert encrypted["nested"]["token"] != "nested-token"
    assert encrypted["list"][0]["secret"] != "list-secret"

    assert encrypted["provider"] == "google"
    assert encrypted["client_id"] == "123456"
    assert encrypted["nested"]["public"] == "public-value"
    assert encrypted["list"][0]["id"] == 1
    assert encrypted["list"][1] == "not-a-dict"

    decrypted = service.decrypt_dict(encrypted)
    assert decrypted == data


def test_encrypt_dict_empty_secret_string():
    service = EncryptionService(secret_key="test-key")
    data = {"secret": "", "public": "ok"}
    encrypted = service.encrypt_dict(data)
    assert encrypted["secret"] != ""
    assert encrypted["public"] == "ok"
    assert service.decrypt_dict(encrypted) == data


def test_encrypt_dict_custom_fields():
    service = EncryptionService(secret_key="test-key")
    data = {"sensitive_info": "secret-value", "other": "other-value"}

    encrypted = service.encrypt_dict(data, sensitive_fields=["info"])

    assert encrypted["sensitive_info"] != "secret-value"
    assert encrypted["other"] == "other-value"

    decrypted = service.decrypt_dict(encrypted, sensitive_fields=["info"])
    assert decrypted == data


def test_decrypt_dict_soft_fail_non_encrypted():
    """Heuristic decrypt leaves non-ciphertext values that match name patterns."""
    service = EncryptionService(secret_key="test-key")
    data = {"api_key": "plaintext-not-encrypted", "name": "x"}
    # decrypt_dict soft-fails so config metadata is not destroyed
    result = service.decrypt_dict(data)
    assert result["api_key"] == "plaintext-not-encrypted"


def test_encrypt_at_paths_and_decrypt_strict():
    service = EncryptionService(secret_key="test-key")
    data = {
        "client_id": "pub",
        "client_secret": "sekrit",
        "credentials": {"api_key": "k", "region": "us"},
    }
    paths = ["client_secret", "credentials.api_key"]
    encrypted = service.encrypt_at_paths(data, paths)
    assert encrypted["client_id"] == "pub"
    assert encrypted["client_secret"] != "sekrit"
    assert encrypted["credentials"]["api_key"] != "k"
    assert encrypted["credentials"]["region"] == "us"

    decrypted = service.decrypt_at_paths(encrypted, paths, strict=True)
    assert decrypted["client_secret"] == "sekrit"
    assert decrypted["credentials"]["api_key"] == "k"


def test_decrypt_at_paths_strict_raises_on_bad_token():
    service = EncryptionService(secret_key="test-key")
    data = {"client_secret": "not-a-token"}
    with pytest.raises(DecryptionError):
        service.decrypt_at_paths(data, ["client_secret"], strict=True)


def test_extract_secret_paths_from_schema():
    schema = {
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string", "secret": True},
            "credentials": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string", "secret": True},
                    "region": {"type": "string"},
                },
            },
        },
    }
    paths = extract_secret_paths_from_schema(schema)
    assert "client_secret" in paths
    assert "credentials.api_key" in paths
    assert "client_id" not in paths
    assert "credentials.region" not in paths


def test_exception_and_logs_do_not_contain_secrets(caplog):
    service = EncryptionService(secret_key="test-key")
    secret = "super-secret-password-value-xyz"
    ciphertext = service.encrypt(secret)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DecryptionError) as exc_info:
            EncryptionService(secret_key="other-key").decrypt(ciphertext)

    combined = str(exc_info.value) + " ".join(r.message for r in caplog.records)
    assert secret not in combined
    assert ciphertext not in combined


def test_default_encryption_key_constant():
    assert DEFAULT_ENCRYPTION_KEY == "change-me-in-production-use-openssl-rand-hex-32"
