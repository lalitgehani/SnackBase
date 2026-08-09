"""FILE-SIZE-*: upload size-limit and memory-DoS guards (M-03).

``upload_file`` does ``content = await file.read()`` and only then computes
``size`` and calls ``validate_file_size``. The limit is therefore enforced
*after* the entire body is already resident in the worker's memory, so the
rejection costs exactly as much RAM as accepting it would have.

The declared ``Content-Length`` is never consulted, and the body is never
consumed in bounded chunks, so the only real ceiling on a single request is
whatever the reverse proxy in front of the app happens to impose.
"""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from starlette.datastructures import UploadFile

from snackbase.core.config import get_settings

# Small enough to keep the test fast, large enough to cross the configured cap.
OVER_LIMIT_PADDING = 1024


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _cleanup(account_id: str) -> None:
    shutil.rmtree(Path(get_settings().storage_path).resolve() / account_id, ignore_errors=True)


@pytest.fixture
def read_call_sizes(monkeypatch: pytest.MonkeyPatch) -> list[int | None]:
    """Record the `size` argument of every `UploadFile.read` the route makes.

    An unbounded read (`read()` with no size) is the signature of "buffer the
    whole body first"; a streaming implementation reads bounded chunks or
    rejects on `Content-Length` before reading at all.
    """
    calls: list[int | None] = []
    original = UploadFile.read

    async def _tracking_read(self: UploadFile, size: int = -1) -> bytes:
        calls.append(None if size == -1 else size)
        return await original(self, size)

    monkeypatch.setattr(UploadFile, "read", _tracking_read)
    return calls


@pytest.mark.asyncio
async def test_file_size_001_over_limit_upload_is_rejected(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FILE-SIZE-001: an over-limit upload is rejected with 400."""
    oversized = b"A" * (get_settings().max_file_size + OVER_LIMIT_PADDING)

    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("big.txt", BytesIO(oversized), "text/plain")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 400
        assert "exceeds maximum allowed" in response.text
    finally:
        _cleanup(security_test_data["account_a"].id)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-03 fix pending", strict=True)
async def test_file_size_002_over_limit_upload_is_not_fully_buffered(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    read_call_sizes: list[int | None],
) -> None:
    """FILE-SIZE-002: rejection must happen before the whole body is in memory."""
    oversized = b"A" * (get_settings().max_file_size + OVER_LIMIT_PADDING)

    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("big.txt", BytesIO(oversized), "text/plain")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 400
        assert None not in read_call_sizes, (
            "the route read the whole body in one unbounded call before "
            "checking the size limit"
        )
    finally:
        _cleanup(security_test_data["account_a"].id)


@pytest.mark.asyncio
async def test_file_size_003_within_limit_upload_succeeds(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FILE-SIZE-003: positive control — a normal upload still succeeds."""
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("small.txt", BytesIO(b"B" * 1024), "text/plain")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 201, response.text
        assert response.json()["file"]["size"] == 1024
    finally:
        _cleanup(security_test_data["account_a"].id)
