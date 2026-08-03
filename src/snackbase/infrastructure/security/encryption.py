"""Fernet-based encryption service for SnackBase credential storage.

Provides strict, fail-closed encryption/decryption for values declared encrypted.
Never returns ciphertext as a successful plaintext substitute.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Sequence
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

# Default encryption key used by Settings when SNACKBASE_ENCRYPTION_KEY is unset.
DEFAULT_ENCRYPTION_KEY = "change-me-in-production-use-openssl-rand-hex-32"

# Stable redaction placeholder used in public API responses.
REDACTION_PLACEHOLDER = "••••••••"


class DecryptionError(Exception):
    """Raised when decryption of a value declared encrypted fails.

    Exception messages must never include plaintext, ciphertext, or keys.
    """

    def __init__(self, message: str = "Decryption failed") -> None:
        super().__init__(message)


class EncryptionService:
    """Encryption service using Fernet symmetric encryption.

    Round-trips text and structured values. Null is preserved at call sites
    (encrypt/decrypt methods accept only non-null strings/values). Empty
    non-null strings are encrypted as real values.
    """

    # Legacy name-based heuristics for configuration encryption during migration
    # to schema-declared secrets. New secret fields should use path-based APIs.
    DEFAULT_SENSITIVE_FIELDS = {
        "secret",
        "token",
        "key",
        "password",
        "cert",
        "access_key",
        "private",
    }

    def __init__(self, secret_key: str):
        """Initialize with a deployment secret key.

        The secret key is hashed with SHA-256 to produce a valid 32-byte Fernet key.
        """
        key_bytes = secret_key.encode("utf-8")
        h = hashlib.sha256(key_bytes).digest()
        fernet_key = base64.urlsafe_b64encode(h)
        self._fernet = Fernet(fernet_key)

    # ------------------------------------------------------------------
    # Strict string encryption
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string (including empty strings).

        Args:
            plaintext: Non-null string to encrypt.

        Returns:
            Base64-encoded Fernet ciphertext.
        """
        ciphertext = self._fernet.encrypt(plaintext.encode("utf-8"))
        return str(ciphertext.decode("utf-8"))

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Fernet ciphertext string.

        Fail-closed: never returns the ciphertext on failure.

        Args:
            ciphertext: Fernet token string.

        Returns:
            Original plaintext string.

        Raises:
            DecryptionError: If the token is malformed or the key is wrong.
        """
        if not isinstance(ciphertext, str):
            raise DecryptionError("Decryption failed")
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return str(plaintext.decode("utf-8"))
        except (InvalidToken, ValueError, TypeError):
            raise DecryptionError("Decryption failed") from None

    def try_decrypt(self, ciphertext: str) -> str | None:
        """Attempt decryption; return None on failure without raising.

        Used only for soft-migration paths where a value may or may not be
        encrypted. Never use for values declared encrypted.
        """
        try:
            return self.decrypt(ciphertext)
        except DecryptionError:
            return None

    # ------------------------------------------------------------------
    # Structured (JSON) value encryption
    # ------------------------------------------------------------------

    def encrypt_structured(self, value: Any) -> str:
        """Serialize a value as canonical JSON and encrypt the payload.

        Supports objects, arrays, strings, numbers, booleans, and null.
        The result is always a Fernet ciphertext string suitable for storage
        in a text or JSON/JSONB column.
        """
        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return self.encrypt(serialized)

    def decrypt_structured(self, ciphertext: str) -> Any:
        """Decrypt a structured value and restore its original JSON type.

        Raises:
            DecryptionError: On decrypt failure or invalid JSON payload.
        """
        plaintext = self.decrypt(ciphertext)
        try:
            return json.loads(plaintext)
        except (json.JSONDecodeError, TypeError):
            raise DecryptionError("Decryption failed") from None

    # ------------------------------------------------------------------
    # Schema path-based encryption (provider configs)
    # ------------------------------------------------------------------

    def encrypt_at_paths(
        self, data: dict[str, Any], secret_paths: Sequence[str]
    ) -> dict[str, Any]:
        """Encrypt string values at dotted paths (e.g. 'credentials.api_key').

        Non-string values at secret paths are JSON-serialized then encrypted.
        Missing paths are ignored. Null values are left as null.
        """
        result = _deep_copy_dict(data)
        for path in secret_paths:
            current: Any = result
            parts = path.split(".")
            for part in parts[:-1]:
                if not isinstance(current, dict) or part not in current:
                    current = None
                    break
                current = current[part]
            if not isinstance(current, dict):
                continue
            leaf = parts[-1]
            if leaf not in current:
                continue
            value = current[leaf]
            if value is None:
                continue
            if isinstance(value, str):
                current[leaf] = self.encrypt(value)
            else:
                current[leaf] = self.encrypt_structured(value)
        return result

    def decrypt_at_paths(
        self, data: dict[str, Any], secret_paths: Sequence[str], *, strict: bool = True
    ) -> dict[str, Any]:
        """Decrypt string values at dotted paths.

        Args:
            data: Configuration dictionary.
            secret_paths: Dotted paths of secret fields.
            strict: When True, raise DecryptionError on failure. When False,
                leave the original value (migration soft path).
        """
        result = _deep_copy_dict(data)
        for path in secret_paths:
            current: Any = result
            parts = path.split(".")
            for part in parts[:-1]:
                if not isinstance(current, dict) or part not in current:
                    current = None
                    break
                current = current[part]
            if not isinstance(current, dict):
                continue
            leaf = parts[-1]
            if leaf not in current:
                continue
            value = current[leaf]
            if value is None or not isinstance(value, str):
                continue
            try:
                # Prefer structured decrypt when the payload looks like JSON
                decrypted = self.decrypt(value)
                try:
                    current[leaf] = json.loads(decrypted)
                except json.JSONDecodeError:
                    current[leaf] = decrypted
            except DecryptionError:
                if strict:
                    raise
                # Soft path: leave as-is
        return result

    # ------------------------------------------------------------------
    # Legacy name-heuristic dict encryption (config registry)
    # ------------------------------------------------------------------

    def encrypt_dict(
        self,
        data: dict[str, Any],
        sensitive_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recursively encrypt sensitive fields by name substring match.

        Empty non-null strings matching sensitive field names are encrypted.
        Prefer encrypt_at_paths with schema-declared secrets for new code.
        """
        fields_to_encrypt = (
            set(sensitive_fields) if sensitive_fields else self.DEFAULT_SENSITIVE_FIELDS
        )
        result: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.encrypt_dict(value, list(fields_to_encrypt))
            elif isinstance(value, list):
                result[key] = [
                    self.encrypt_dict(item, list(fields_to_encrypt))
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            elif (
                any(field in key.lower() for field in fields_to_encrypt)
                and isinstance(value, str)
            ):
                # Encrypt including empty strings; null is not a str so skipped
                result[key] = self.encrypt(value)
            else:
                result[key] = value

        return result

    def decrypt_dict(
        self,
        data: dict[str, Any],
        sensitive_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recursively decrypt sensitive fields by name substring match.

        Soft-fail for heuristic paths: if decryption fails, the original value
        is retained so non-encrypted metadata that matches name heuristics is
        not destroyed. Values declared encrypted via path-based APIs must use
        decrypt_at_paths(strict=True) instead.
        """
        fields_to_decrypt = (
            set(sensitive_fields) if sensitive_fields else self.DEFAULT_SENSITIVE_FIELDS
        )
        result: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.decrypt_dict(value, list(fields_to_decrypt))
            elif isinstance(value, list):
                result[key] = [
                    self.decrypt_dict(item, list(fields_to_decrypt))
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            elif (
                any(field in key.lower() for field in fields_to_decrypt)
                and isinstance(value, str)
                and value
            ):
                decrypted = self.try_decrypt(value)
                result[key] = decrypted if decrypted is not None else value
            else:
                result[key] = value

        return result


def _deep_copy_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Shallow-recursive copy of a dict tree for path-based mutation."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _deep_copy_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _deep_copy_dict(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            result[key] = value
    return result


def extract_secret_paths_from_schema(
    schema: dict[str, Any] | None, prefix: str = ""
) -> list[str]:
    """Extract dotted paths marked ``secret: true`` from a JSON Schema object.

    Supports nested ``properties`` objects. Returns paths relative to the root
    config object (e.g. ``client_secret``, ``credentials.api_key``).
    """
    if not schema or not isinstance(schema, dict):
        return []

    paths: list[str] = []
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return paths

    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        path = f"{prefix}.{name}" if prefix else name
        if prop.get("secret") is True:
            paths.append(path)
        # Recurse into nested objects
        if prop.get("type") == "object" or "properties" in prop:
            paths.extend(extract_secret_paths_from_schema(prop, path))
    return paths
