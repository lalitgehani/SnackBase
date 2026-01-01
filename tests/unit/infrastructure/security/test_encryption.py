import pytest
from snackbase.infrastructure.security.encryption import EncryptionService


def test_encryption_round_trip():
    service = EncryptionService(secret_key="test-secret-key")
    plaintext = "Hello, SnackBase!"

    ciphertext = service.encrypt(plaintext)
    assert ciphertext != plaintext

    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encryption_different_keys():
    service1 = EncryptionService(secret_key="key-1")
    service2 = EncryptionService(secret_key="key-2")
    plaintext = "Sensitive data"

    ciphertext1 = service1.encrypt(plaintext)
    decrypted2 = service2.decrypt(ciphertext1)

    # Decryption with wrong key should fail and return original ciphertext
    assert decrypted2 == ciphertext1


def test_decrypt_invalid_ciphertext():
    service = EncryptionService(secret_key="test-key")
    invalid_ciphertext = "not-a-fernet-token"

    decrypted = service.decrypt(invalid_ciphertext)
    assert decrypted == invalid_ciphertext


def test_encrypt_decrypt_dict():
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

    # Sensitive fields should be encrypted
    assert encrypted["client_secret"] != "super-secret-password"
    assert encrypted["api_key"] != "api-key-value"
    assert encrypted["nested"]["token"] != "nested-token"
    assert encrypted["list"][0]["secret"] != "list-secret"

    # Non-sensitive fields should remain unchanged
    assert encrypted["provider"] == "google"
    assert encrypted["client_id"] == "123456"
    assert encrypted["nested"]["public"] == "public-value"
    assert encrypted["list"][0]["id"] == 1
    assert encrypted["list"][1] == "not-a-dict"

    decrypted = service.decrypt_dict(encrypted)
    assert decrypted == data


def test_encrypt_dict_custom_fields():
    service = EncryptionService(secret_key="test-key")
    data = {"sensitive_info": "secret-value", "other": "other-value"}

    # Only encrypt "sensitive_info"
    encrypted = service.encrypt_dict(data, sensitive_fields=["info"])

    assert encrypted["sensitive_info"] != "secret-value"
    assert encrypted["other"] == "other-value"

    decrypted = service.decrypt_dict(encrypted, sensitive_fields=["info"])
    assert decrypted == data


def test_encryption_empty_values():
    service = EncryptionService(secret_key="test-key")

    assert service.encrypt("") == ""
    assert service.decrypt("") == ""

    data = {"secret": ""}
    assert service.encrypt_dict(data) == data
