"""Unit tests for collection field encryption pipeline helpers."""

import pytest

from snackbase.infrastructure.security.encryption import (
    REDACTION_PLACEHOLDER,
    DecryptionError,
    EncryptionService,
)
from snackbase.infrastructure.security.field_encryption import (
    assert_no_encrypted_in_query,
    decrypt_record_fields,
    encrypt_record_for_storage,
    prepare_write_payload,
    redact_record_for_response,
)

SCHEMA = [
    {"name": "title", "type": "text"},
    {"name": "api_token", "type": "text", "encrypted": True},
    {"name": "creds", "type": "json", "encrypted": True},
]


def test_encrypt_decrypt_text_and_json_round_trip():
    enc = EncryptionService("test-key")
    data = {
        "title": "Hello",
        "api_token": "secret-token",
        "creds": {"k": "v", "n": 1},
    }
    stored = encrypt_record_for_storage(data, SCHEMA, enc)
    assert stored["title"] == "Hello"
    assert stored["api_token"] != "secret-token"
    assert stored["creds"] != data["creds"]
    assert isinstance(stored["creds"], str)

    decrypted = decrypt_record_fields(stored, SCHEMA, enc)
    assert decrypted["api_token"] == "secret-token"
    assert decrypted["creds"] == {"k": "v", "n": 1}


def test_null_stays_null():
    enc = EncryptionService("test-key")
    data = {"api_token": None, "title": "x"}
    stored = encrypt_record_for_storage(data, SCHEMA, enc)
    assert stored["api_token"] is None


def test_empty_string_encrypts():
    enc = EncryptionService("test-key")
    data = {"api_token": ""}
    stored = encrypt_record_for_storage(data, SCHEMA, enc)
    assert stored["api_token"] != ""
    assert decrypt_record_fields(stored, SCHEMA, enc)["api_token"] == ""


def test_redact_for_response():
    record = {"title": "t", "api_token": "ciphertext", "creds": None}
    redacted = redact_record_for_response(record, SCHEMA)
    assert redacted["title"] == "t"
    assert redacted["api_token"] == REDACTION_PLACEHOLDER
    assert redacted["creds"] is None


def test_prepare_write_strips_placeholder():
    data = {"title": "t", "api_token": REDACTION_PLACEHOLDER}
    prepared = prepare_write_payload(data, SCHEMA, partial=True)
    assert "api_token" not in prepared
    assert prepared["title"] == "t"


def test_decrypt_failure_raises():
    enc = EncryptionService("test-key")
    with pytest.raises(DecryptionError):
        decrypt_record_fields(
            {"api_token": "not-ciphertext"}, SCHEMA, enc, field_names=["api_token"]
        )


def test_assert_no_encrypted_in_query():
    err = assert_no_encrypted_in_query(SCHEMA, sort_by="api_token")
    assert err is not None and "api_token" in err

    err = assert_no_encrypted_in_query(SCHEMA, filter_expr='api_token = "x"')
    assert err is not None

    err = assert_no_encrypted_in_query(SCHEMA, sort_by="title", filter_expr='title = "x"')
    assert err is None
