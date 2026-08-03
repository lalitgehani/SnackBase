"""Response helpers for function handlers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Response:
    """HTTP response returned by a function handler."""

    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    body_text: str | None = None
    stream: Iterator[bytes] | AsyncIterator[bytes] | None = None
    media_type: str | None = None

    @classmethod
    def json(
        cls,
        data: Any,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Return a JSON response."""
        hdrs = {"content-type": "application/json", **(headers or {})}
        return cls(status_code=status, headers=hdrs, body=data, media_type="application/json")

    @classmethod
    def text(
        cls,
        content: str,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Return a plain-text response."""
        hdrs = {"content-type": "text/plain; charset=utf-8", **(headers or {})}
        return cls(
            status_code=status,
            headers=hdrs,
            body_text=content,
            media_type="text/plain; charset=utf-8",
        )

    @classmethod
    def stream_response(
        cls,
        chunks: Iterator[bytes] | AsyncIterator[bytes],
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str = "text/event-stream",
    ) -> Response:
        """Return a streaming response (SSE/chunked)."""
        hdrs = {"content-type": media_type, **(headers or {})}
        return cls(
            status_code=status,
            headers=hdrs,
            stream=chunks,
            media_type=media_type,
        )

    def to_envelope(self) -> dict[str, Any]:
        """Serialize to the bootstrap JSON envelope (non-streaming)."""
        return {
            "status": "success",
            "http_status": self.status_code,
            "headers": self.headers,
            "body": self.body if self.body is not None else self.body_text,
            "streaming": self.stream is not None,
            "media_type": self.media_type,
        }
