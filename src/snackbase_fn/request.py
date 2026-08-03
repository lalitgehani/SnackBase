"""Request object passed to function handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuthContext:
    """Caller authentication context injected by the runner."""

    user_id: str | None = None
    email: str | None = None
    account_id: str | None = None
    role: str | None = None


@dataclass
class Request:
    """HTTP request view available to function handlers."""

    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)
    json: Any = None
    body_bytes: bytes = b""
    auth: AuthContext = field(default_factory=AuthContext)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Request:
        """Build a Request from the bootstrap JSON envelope."""
        auth_raw = payload.get("auth") or {}
        body = payload.get("body")
        body_bytes = payload.get("body_bytes")
        if isinstance(body_bytes, str):
            body_bytes_val = body_bytes.encode("utf-8")
        elif isinstance(body_bytes, (bytes, bytearray)):
            body_bytes_val = bytes(body_bytes)
        else:
            body_bytes_val = b""
        headers = {str(k).lower(): str(v) for k, v in (payload.get("headers") or {}).items()}
        return cls(
            method=str(payload.get("method") or "POST").upper(),
            path=str(payload.get("path") or "/"),
            headers=headers,
            query=dict(payload.get("query") or {}),
            json=body if body is not None else payload.get("json"),
            body_bytes=body_bytes_val,
            auth=AuthContext(
                user_id=auth_raw.get("user_id"),
                email=auth_raw.get("email"),
                account_id=auth_raw.get("account_id"),
                role=auth_raw.get("role"),
            ),
        )
