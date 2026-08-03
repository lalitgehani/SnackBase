"""Redaction helpers for function execution logs."""

from __future__ import annotations

from typing import Any

from snackbase.infrastructure.security.encryption import REDACTION_PLACEHOLDER

_SENSITIVE_HEADER_TOKENS = ("secret", "token", "key", "authorization", "cookie", "password")


def _is_sensitive_header(name: str) -> bool:
    lowered = name.lower()
    if lowered in {"authorization", "cookie", "set-cookie", "x-api-key"}:
        return True
    return any(token in lowered for token in _SENSITIVE_HEADER_TOKENS)


def redact_headers(headers: dict[str, Any] | None) -> dict[str, Any]:
    if not headers:
        return {}
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        if _is_sensitive_header(str(key)):
            redacted[str(key)] = REDACTION_PLACEHOLDER
        else:
            redacted[str(key)] = value
    return redacted


def truncate_text(value: str | None, max_bytes: int = 65_536) -> str | None:
    if value is None:
        return None
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "…[truncated]"


def redact_request_data(
    *,
    method: str,
    path: str,
    headers: dict[str, Any] | None,
    query: dict[str, Any] | None,
    body: Any,
    max_body_chars: int = 8_192,
) -> dict[str, Any]:
    """Build a redacted request snapshot for execution logs."""
    body_out: Any = body
    if isinstance(body, str) and len(body) > max_body_chars:
        body_out = body[:max_body_chars] + "…[truncated]"
    elif isinstance(body, (bytes, bytearray)):
        body_out = f"<{len(body)} bytes>"
    return {
        "method": method,
        "path": path,
        "headers": redact_headers(headers),
        "query": query or {},
        "body": body_out,
    }
