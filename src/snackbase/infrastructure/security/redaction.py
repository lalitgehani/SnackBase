"""Shared secret redaction helpers for API responses, audit, and events.

Encrypted collection fields and schema-declared configuration secrets must
never appear as plaintext outside the scoped reveal endpoint or trusted
provider runtime code.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from snackbase.infrastructure.security.encryption import (
    REDACTION_PLACEHOLDER,
    extract_secret_paths_from_schema,
)


def get_encrypted_field_names(schema: Sequence[Mapping[str, Any]] | None) -> list[str]:
    """Return field names marked ``encrypted: true`` in a collection schema."""
    if not schema:
        return []
    names: list[str] = []
    for field in schema:
        if not isinstance(field, Mapping):
            continue
        if field.get("encrypted") is True:
            name = field.get("name")
            if isinstance(name, str) and name:
                names.append(name)
    return names


def is_redaction_placeholder(value: Any) -> bool:
    """Return True if value is the public redaction placeholder."""
    return bool(value == REDACTION_PLACEHOLDER)


def redact_record_fields(
    record: dict[str, Any],
    encrypted_fields: Iterable[str],
    *,
    placeholder: str = REDACTION_PLACEHOLDER,
) -> dict[str, Any]:
    """Return a shallow copy of record with encrypted fields redacted.

    Null encrypted fields remain null (no secret present). Non-null values
    (ciphertext or accidental plaintext) are replaced with the placeholder.
    """
    encrypted_set = set(encrypted_fields)
    if not encrypted_set:
        return dict(record)

    redacted = dict(record)
    for name in encrypted_set:
        if name not in redacted:
            continue
        if redacted[name] is None:
            continue
        redacted[name] = placeholder
    return redacted


def redact_records(
    records: Sequence[dict[str, Any]],
    encrypted_fields: Iterable[str],
    *,
    placeholder: str = REDACTION_PLACEHOLDER,
) -> list[dict[str, Any]]:
    """Redact a list of records."""
    fields = list(encrypted_fields)
    return [redact_record_fields(r, fields, placeholder=placeholder) for r in records]


def redact_config_secrets(
    config: dict[str, Any],
    secret_paths: Sequence[str],
    *,
    placeholder: str = REDACTION_PLACEHOLDER,
) -> dict[str, Any]:
    """Mask schema-declared secret paths in a configuration dictionary.

    Null secrets remain null. Non-null secrets become the placeholder.
    """
    result = _deep_copy(config)
    for path in secret_paths:
        parts = path.split(".")
        current: Any = result
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
        if current[leaf] is None:
            continue
        current[leaf] = placeholder
    return result


def redact_config_with_schema(
    config: dict[str, Any],
    config_schema: dict[str, Any] | None,
    *,
    placeholder: str = REDACTION_PLACEHOLDER,
) -> dict[str, Any]:
    """Mask secrets using paths extracted from a provider JSON schema."""
    paths = extract_secret_paths_from_schema(config_schema)
    if not paths:
        return dict(config)
    return redact_config_secrets(config, paths, placeholder=placeholder)


def strip_secrets_from_audit_values(
    values: dict[str, Any] | None,
    secret_fields: Iterable[str],
    *,
    placeholder: str = REDACTION_PLACEHOLDER,
) -> dict[str, Any] | None:
    """Redact secret field values before audit log serialization.

    Returns None when input is None. Field names remain; only values change.
    """
    if values is None:
        return None
    return redact_record_fields(values, secret_fields, placeholder=placeholder)


def safe_error_detail(message: str) -> dict[str, str]:
    """Build an error detail dict that never embeds secret values.

    Callers must pass a static or sanitized message, never request bodies.
    """
    return {"error": message}


def _deep_copy(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _deep_copy(value)
        elif isinstance(value, list):
            result[key] = [
                _deep_copy(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            result[key] = value
    return result
