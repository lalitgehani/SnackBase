"""Unit tests for shared secret redaction helpers."""

from snackbase.infrastructure.security.encryption import REDACTION_PLACEHOLDER
from snackbase.infrastructure.security.redaction import (
    get_encrypted_field_names,
    is_redaction_placeholder,
    redact_config_secrets,
    redact_config_with_schema,
    redact_record_fields,
    redact_records,
    strip_secrets_from_audit_values,
)


def test_get_encrypted_field_names():
    schema = [
        {"name": "title", "type": "text"},
        {"name": "api_token", "type": "text", "encrypted": True},
        {"name": "meta", "type": "json", "encrypted": True},
    ]
    assert get_encrypted_field_names(schema) == ["api_token", "meta"]
    assert get_encrypted_field_names(None) == []


def test_redact_record_fields_preserves_null():
    record = {"title": "x", "api_token": "ciphertext", "empty_secret": None}
    redacted = redact_record_fields(record, ["api_token", "empty_secret"])
    assert redacted["title"] == "x"
    assert redacted["api_token"] == REDACTION_PLACEHOLDER
    assert redacted["empty_secret"] is None
    # Original unchanged
    assert record["api_token"] == "ciphertext"


def test_redact_records():
    records = [{"a": "1", "s": "c"}, {"a": "2", "s": "d"}]
    out = redact_records(records, ["s"])
    assert all(r["s"] == REDACTION_PLACEHOLDER for r in out)


def test_is_redaction_placeholder():
    assert is_redaction_placeholder(REDACTION_PLACEHOLDER)
    assert not is_redaction_placeholder("secret")


def test_redact_config_with_schema():
    schema = {
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string", "secret": True},
        },
    }
    config = {"client_id": "id", "client_secret": "sekrit"}
    masked = redact_config_with_schema(config, schema)
    assert masked["client_id"] == "id"
    assert masked["client_secret"] == REDACTION_PLACEHOLDER


def test_redact_config_nested_paths():
    config = {"credentials": {"api_key": "k", "region": "us"}}
    masked = redact_config_secrets(config, ["credentials.api_key"])
    assert masked["credentials"]["api_key"] == REDACTION_PLACEHOLDER
    assert masked["credentials"]["region"] == "us"


def test_strip_secrets_from_audit_values():
    values = {"name": "n", "token": "plain"}
    out = strip_secrets_from_audit_values(values, ["token"])
    assert out is not None
    assert out["token"] == REDACTION_PLACEHOLDER
    assert out["name"] == "n"
    assert strip_secrets_from_audit_values(None, ["token"]) is None
