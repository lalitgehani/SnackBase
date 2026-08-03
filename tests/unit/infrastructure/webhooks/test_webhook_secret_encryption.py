"""Unit tests for encrypted webhook signing secrets."""

from snackbase.core.config import get_settings
from snackbase.infrastructure.security.encryption import EncryptionService
from snackbase.infrastructure.webhooks.webhook_service import (
    resolve_webhook_signing_secret,
    sign_payload,
)


def test_sign_payload_stable_with_plaintext():
    body = b'{"event":"test"}'
    sig = sign_payload("my-secret", body)
    assert sig.startswith("sha256=")
    assert sign_payload("my-secret", body) == sig


def test_resolve_decrypts_fernet_secret():
    service = EncryptionService(get_settings().encryption_key)
    plain = "webhook-signing-secret-value"
    stored = service.encrypt(plain)
    assert stored != plain
    assert resolve_webhook_signing_secret(stored) == plain


def test_resolve_accepts_legacy_plaintext():
    legacy = "legacy-plaintext-secret"
    assert resolve_webhook_signing_secret(legacy) == legacy


def test_signing_works_after_encrypt_round_trip():
    service = EncryptionService(get_settings().encryption_key)
    plain = "sign-me-please"
    body = b'{"a":1}'
    expected = sign_payload(plain, body)
    stored = service.encrypt(plain)
    resolved = resolve_webhook_signing_secret(stored)
    assert sign_payload(resolved, body) == expected
