"""Unit tests for function execution log redaction."""

from snackbase.infrastructure.functions.redaction import redact_request_data
from snackbase.infrastructure.security.encryption import REDACTION_PLACEHOLDER


def test_redact_authorization_header() -> None:
    data = redact_request_data(
        method="POST",
        path="/",
        headers={"Authorization": "Bearer secret-token", "Content-Type": "application/json"},
        query={},
        body={"x": 1},
    )
    assert data["headers"]["Authorization"] == REDACTION_PLACEHOLDER
    assert data["headers"]["Content-Type"] == "application/json"
    assert data["body"] == {"x": 1}


def test_redact_token_like_headers() -> None:
    data = redact_request_data(
        method="GET",
        path="/",
        headers={"X-Api-Key": "abc", "X-Custom-Token": "t", "Accept": "json"},
        query=None,
        body=None,
    )
    assert data["headers"]["X-Api-Key"] == REDACTION_PLACEHOLDER
    assert data["headers"]["X-Custom-Token"] == REDACTION_PLACEHOLDER
    assert data["headers"]["Accept"] == "json"
