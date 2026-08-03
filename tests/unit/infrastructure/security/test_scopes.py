"""Unit tests for API-key scope helpers."""

import pytest

from snackbase.infrastructure.security.scopes import (
    APPROVED_SCOPES,
    SCOPE_RECORDS_SECRETS_READ,
    has_scope,
    is_approved_scope,
    validate_scopes,
)


def test_records_secrets_read_is_approved():
    assert SCOPE_RECORDS_SECRETS_READ == "records:secrets:read"
    assert is_approved_scope(SCOPE_RECORDS_SECRETS_READ)
    assert SCOPE_RECORDS_SECRETS_READ in APPROVED_SCOPES


def test_validate_scopes_empty():
    assert validate_scopes(None) == []
    assert validate_scopes([]) == []


def test_validate_scopes_dedupes():
    result = validate_scopes(
        [SCOPE_RECORDS_SECRETS_READ, SCOPE_RECORDS_SECRETS_READ]
    )
    assert result == [SCOPE_RECORDS_SECRETS_READ]


def test_validate_scopes_rejects_unknown():
    with pytest.raises(ValueError, match="Unapproved"):
        validate_scopes(["admin:all", SCOPE_RECORDS_SECRETS_READ])


def test_has_scope():
    assert has_scope([SCOPE_RECORDS_SECRETS_READ], SCOPE_RECORDS_SECRETS_READ)
    assert not has_scope([], SCOPE_RECORDS_SECRETS_READ)
    assert not has_scope(None, SCOPE_RECORDS_SECRETS_READ)
