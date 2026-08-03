"""Security suite: no plaintext leak for designated secret surfaces."""

from snackbase.infrastructure.security.encryption import (
    REDACTION_PLACEHOLDER,
    EncryptionService,
)
from snackbase.infrastructure.security.field_encryption import (
    encrypt_record_for_storage,
    redact_record_for_response,
)
from snackbase.infrastructure.security.redaction import (
    get_encrypted_field_names,
    redact_config_with_schema,
)
from snackbase.infrastructure.security.scopes import (
    SCOPE_RECORDS_SECRETS_READ,
    has_scope,
)

SCHEMA = [
    {"name": "title", "type": "text"},
    {"name": "api_token", "type": "text", "encrypted": True},
]


def test_public_record_response_never_contains_plaintext_or_ciphertext():
    enc = EncryptionService("sec-key")
    stored = encrypt_record_for_storage(
        {"title": "t", "api_token": "super-secret-value"}, SCHEMA, enc
    )
    public = redact_record_for_response(stored, SCHEMA)
    assert public["api_token"] == REDACTION_PLACEHOLDER
    assert "super-secret-value" not in str(public)
    assert stored["api_token"] not in str(public)


def test_db_row_ciphertext_differs_from_plaintext():
    enc = EncryptionService("sec-key")
    plain = "db-secret-value"
    stored = encrypt_record_for_storage({"api_token": plain}, SCHEMA, enc)
    assert stored["api_token"] != plain
    assert plain not in stored["api_token"]


def test_config_admin_masking_no_plaintext():
    schema = {
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string", "secret": True},
        },
    }
    masked = redact_config_with_schema(
        {"client_id": "id", "client_secret": "plain-secret"}, schema
    )
    assert masked["client_secret"] == REDACTION_PLACEHOLDER
    assert "plain-secret" not in str(masked)


def test_missing_scope_cannot_reveal():
    assert not has_scope([], SCOPE_RECORDS_SECRETS_READ)
    assert not has_scope(None, SCOPE_RECORDS_SECRETS_READ)
    assert has_scope([SCOPE_RECORDS_SECRETS_READ], SCOPE_RECORDS_SECRETS_READ)


def test_encrypted_field_names_discovery():
    assert get_encrypted_field_names(SCHEMA) == ["api_token"]
