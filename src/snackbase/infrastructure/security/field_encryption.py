"""Encrypt and redact collection record fields marked ``encrypted: true``.

Write path: encrypt plaintext before INSERT/UPDATE.
Read path (public API): always redact; never return ciphertext or plaintext.
Trusted path (secret reveal / future server hooks): decrypt strictly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from snackbase.infrastructure.security.encryption import (
    DecryptionError,
    EncryptionService,
)
from snackbase.infrastructure.security.redaction import (
    get_encrypted_field_names,
    is_redaction_placeholder,
    redact_record_fields,
)

# Types allowed to be marked encrypted
ENCRYPTED_ALLOWED_TYPES = frozenset({"text", "json"})


def get_encrypted_fields(schema: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Return field definition dicts that are encrypted."""
    if not schema:
        return []
    result: list[dict[str, Any]] = []
    for field in schema:
        if field.get("encrypted") is True:
            result.append(dict(field))
    return result


def encrypt_value_for_field(
    value: Any,
    field_type: str,
    encryption: EncryptionService,
) -> Any:
    """Encrypt a single field value for database storage.

    null stays null. Empty strings are encrypted. JSON values are serialized
    then encrypted; the stored form is the ciphertext string (for both text
    and json columns).
    """
    if value is None:
        return None
    ft = field_type.lower()
    if ft == "json":
        return encryption.encrypt_structured(value)
    # text and any other allowed type: coerce to string
    if not isinstance(value, str):
        value = str(value)
    return encryption.encrypt(value)


def decrypt_value_for_field(
    value: Any,
    field_type: str,
    encryption: EncryptionService,
) -> Any:
    """Strictly decrypt a stored field value.

    Raises:
        DecryptionError: On failure (never returns ciphertext).
    """
    if value is None:
        return None
    if not isinstance(value, str):
        # JSON columns may surface already-parsed values incorrectly; fail closed
        raise DecryptionError("Decryption failed")
    ft = field_type.lower()
    if ft == "json":
        return encryption.decrypt_structured(value)
    return encryption.decrypt(value)


def encrypt_record_for_storage(
    data: dict[str, Any],
    schema: Sequence[Mapping[str, Any]],
    encryption: EncryptionService,
) -> dict[str, Any]:
    """Return a copy of data with encrypted fields replaced by ciphertext.

    Only keys present in ``data`` are processed (PATCH-friendly).
    """
    schema_lookup = {f["name"]: f for f in schema if isinstance(f, Mapping)}
    result = dict(data)
    for name, value in list(result.items()):
        field = schema_lookup.get(name)
        if not field or field.get("encrypted") is not True:
            continue
        field_type = str(field.get("type", "text")).lower()
        result[name] = encrypt_value_for_field(value, field_type, encryption)
    return result


def decrypt_record_fields(
    record: dict[str, Any],
    schema: Sequence[Mapping[str, Any]],
    encryption: EncryptionService,
    field_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Decrypt selected encrypted fields strictly. Returns only those fields.

    Args:
        record: Record with ciphertext values.
        schema: Collection schema.
        encryption: Encryption service.
        field_names: Optional subset; default all encrypted fields present.
    """
    encrypted = get_encrypted_fields(schema)
    by_name = {f["name"]: f for f in encrypted}
    if field_names is None:
        targets = [n for n in by_name if n in record]
    else:
        targets = list(field_names)

    out: dict[str, Any] = {}
    for name in targets:
        field = by_name.get(name)
        if field is None:
            continue
        if name not in record:
            continue
        field_type = str(field.get("type", "text")).lower()
        out[name] = decrypt_value_for_field(record[name], field_type, encryption)
    return out


def prepare_write_payload(
    data: dict[str, Any],
    schema: Sequence[Mapping[str, Any]],
    *,
    partial: bool = False,
) -> dict[str, Any]:
    """Prepare request data before encryption.

    - Drops redaction placeholders so they never overwrite secrets.
    - On partial updates, omitted encrypted fields are already absent.
    """
    encrypted_names = set(get_encrypted_field_names(schema))
    result = dict(data)
    for name in encrypted_names:
        if name not in result:
            continue
        if is_redaction_placeholder(result[name]):
            # Preserve existing secret: remove from write set
            del result[name]
    return result


def redact_record_for_response(
    record: dict[str, Any],
    schema: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Redact encrypted fields in a single record for public API responses."""
    names = get_encrypted_field_names(schema)
    return redact_record_fields(record, names)


def redact_records_for_response(
    records: Sequence[dict[str, Any]],
    schema: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Redact encrypted fields across a list of records."""
    names = get_encrypted_field_names(schema)
    return [redact_record_fields(r, names) for r in records]


def assert_no_encrypted_in_query(
    schema: Sequence[Mapping[str, Any]],
    *,
    sort_by: str | None = None,
    filter_expr: str | None = None,
    group_by: Sequence[str] | None = None,
    agg_expr: str | None = None,
) -> str | None:
    """Return an error message if a query references an encrypted field.

    Simple containment checks for filter/agg expressions; exact match for sort
    and group-by field names.
    """
    names = get_encrypted_field_names(schema)
    if not names:
        return None
    name_set = set(names)

    if sort_by and sort_by in name_set:
        return (
            f"Cannot sort by encrypted field '{sort_by}'. "
            "Encrypted fields are non-queryable."
        )

    if group_by:
        for g in group_by:
            if g in name_set:
                return (
                    f"Cannot group by encrypted field '{g}'. "
                    "Encrypted fields are non-queryable."
                )

    # Tokenize-ish: reject if encrypted field name appears as a whole identifier
    for expr in (filter_expr, agg_expr):
        if not expr:
            continue
        for name in names:
            # Word-boundary-ish check without regex dependency issues
            if _contains_identifier(expr, name):
                return (
                    f"Cannot filter, search, or aggregate on encrypted field '{name}'. "
                    "Encrypted fields are non-queryable."
                )
    return None


def _contains_identifier(expression: str, name: str) -> bool:
    """Return True if ``name`` appears as an identifier in the expression."""
    import re

    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", expression) is not None
