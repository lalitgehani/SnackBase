"""FILE-TRV-*: cross-tenant file path-traversal regression guards (C-01).

The confinement check in ``FileStorageService.get_file_path`` verifies two
things that together are not enough:

1. the requested path starts with ``"<account_id>/"``; and
2. the *resolved* path stays under the storage root.

A payload of ``"<A>/../<B>/f.txt"`` satisfies both — it starts with A's prefix,
and after resolution it lands in B's directory, which is still inside the
storage root. The guard misses the *sideways* traversal into a sibling tenant,
which is precisely the multi-tenant boundary it exists to protect.

The secure behaviour these tests assert is: the path must resolve inside the
caller's *own account directory*, not merely inside the storage root.
"""

import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest
from httpx import AsyncClient

from snackbase.core.config import get_settings
from snackbase.domain.services.file_storage_service import FileStorageService
from tests.security.helpers import assert_denied

ALPHA_MARKER = "ALPHA-FILE-SECRET"


# ---------------------------------------------------------------------------
# Unit level — the service guard itself
# ---------------------------------------------------------------------------


@pytest.fixture
def sibling_tenants() -> Any:
    """A storage root holding one file for tenant A and one for tenant B."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "AB1111").mkdir()
        (root / "AB2222").mkdir()
        (root / "AB1111" / "alpha.txt").write_text(ALPHA_MARKER)
        (root / "AB2222" / "beta.txt").write_text("BETA-FILE-SECRET")
        yield {
            "service": FileStorageService(storage_path=str(root)),
            "root": root,
            "victim": "AB1111",
            "attacker": "AB2222",
        }


def test_file_trv_001_get_file_path_rejects_sibling_account_traversal(
    sibling_tenants: dict[str, Any],
) -> None:
    """FILE-TRV-001: `<B>/../<A>/f` must not resolve into A's directory."""
    service: FileStorageService = sibling_tenants["service"]
    payload = f"{sibling_tenants['attacker']}/../{sibling_tenants['victim']}/alpha.txt"

    with pytest.raises(ValueError, match="Invalid file path"):
        service.get_file_path(sibling_tenants["attacker"], payload)


def test_file_trv_002_delete_file_rejects_sibling_account_traversal(
    sibling_tenants: dict[str, Any],
) -> None:
    """FILE-TRV-002: the same payload must not let B delete A's file."""
    service: FileStorageService = sibling_tenants["service"]
    payload = f"{sibling_tenants['attacker']}/../{sibling_tenants['victim']}/alpha.txt"

    with pytest.raises(ValueError, match="Invalid file path"):
        service.delete_file(sibling_tenants["attacker"], payload)

    assert (sibling_tenants["root"] / "AB1111" / "alpha.txt").exists(), (
        "victim's file was deleted by a sibling-account traversal"
    )


def test_file_trv_003_escape_from_storage_root_still_rejected(
    sibling_tenants: dict[str, Any],
) -> None:
    """FILE-TRV-003: the pre-existing upward-escape guard is unchanged."""
    service: FileStorageService = sibling_tenants["service"]

    with pytest.raises(ValueError, match="Invalid file path"):
        service.get_file_path("AB1111", "AB1111/../../../etc/passwd")


def test_file_trv_004_own_account_path_still_resolves(
    sibling_tenants: dict[str, Any],
) -> None:
    """FILE-TRV-004: positive control — a normal path still works."""
    service: FileStorageService = sibling_tenants["service"]

    resolved = service.get_file_path("AB1111", "AB1111/alpha.txt")

    assert resolved.read_text() == ALPHA_MARKER


# ---------------------------------------------------------------------------
# Integration level — the dispatcher
# ---------------------------------------------------------------------------


async def _raw_asgi_get(path: str, token: str) -> Any:
    """Issue a GET whose path is *not* dot-segment normalised.

    httpx (like a browser) collapses ``..`` client-side, so a normal
    ``client.get()`` cannot express this attack. A raw HTTP client
    (``curl --path-as-is``) or a permissive proxy can, so the request is built
    at the ASGI layer to model that.
    """
    from snackbase.infrastructure.api.app import app

    body_chunks: list[bytes] = []
    status: dict[str, int] = {}

    raw_path = path.encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": unquote(path),
        "raw_path": raw_path,
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"test"),
            (b"authorization", f"Bearer {token}".encode()),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            status["code"] = message["status"]
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    await app(scope, receive, send)

    class _RawResponse:
        status_code = status.get("code", 0)
        text = b"".join(body_chunks).decode(errors="replace")

    return _RawResponse()


@pytest.mark.asyncio
async def test_file_trv_010_raw_traversal_denied_over_http(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_files: dict[str, Any],
) -> None:
    """FILE-TRV-010: B cannot read A's file via an un-normalised `../`."""
    account_b = security_test_data["account_b"]
    victim_path = two_tenant_files["account_a_path"]

    response = await _raw_asgi_get(
        f"/api/v1/files/{account_b.id}/../{victim_path}",
        security_test_data["user_b_token"],
    )

    assert_denied(response, leak_markers=(two_tenant_files["account_a_marker"],))


@pytest.mark.asyncio
async def test_file_trv_011_encoded_traversal_denied_over_http(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_files: dict[str, Any],
) -> None:
    """FILE-TRV-011: the URL-encoded `..%2f` variant is equally denied."""
    account_b = security_test_data["account_b"]
    victim_path = two_tenant_files["account_a_path"]

    response = await client.get(
        f"/api/v1/files/{account_b.id}/..%2f{victim_path}",
        headers={"Authorization": f"Bearer {security_test_data['user_b_token']}"},
    )

    assert_denied(response, leak_markers=(two_tenant_files["account_a_marker"],))


@pytest.mark.asyncio
async def test_file_trv_012_owner_download_still_works(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_files: dict[str, Any],
) -> None:
    """FILE-TRV-012: positive control — A can still download A's own file."""
    response = await client.get(
        f"/api/v1/files/{two_tenant_files['account_a_path']}",
        headers={"Authorization": f"Bearer {security_test_data['user_a_token']}"},
    )

    assert response.status_code == 200
    assert two_tenant_files["account_a_marker"] in response.text


@pytest.mark.asyncio
async def test_file_trv_013_plain_cross_account_download_denied(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_files: dict[str, Any],
) -> None:
    """FILE-TRV-013: the non-traversal cross-account read stays denied."""
    response = await client.get(
        f"/api/v1/files/{two_tenant_files['account_a_path']}",
        headers={"Authorization": f"Bearer {security_test_data['user_b_token']}"},
    )

    assert_denied(response, leak_markers=(two_tenant_files["account_a_marker"],))


@pytest.mark.asyncio
async def test_file_trv_014_upload_ignores_traversal_in_filename(
    client: AsyncClient,
    security_test_data: dict[str, Any],
) -> None:
    """FILE-TRV-014: a `../` filename cannot place a file outside the account dir."""
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("../../escape.txt", BytesIO(b"escaped"), "text/plain")},
        headers={"Authorization": f"Bearer {security_test_data['user_a_token']}"},
    )

    assert response.status_code == 201, response.text
    stored_path = response.json()["file"]["path"]
    assert stored_path.startswith(f"{security_test_data['account_a'].id}/")
    assert ".." not in stored_path

    storage_root = Path(get_settings().storage_path).resolve()
    shutil.rmtree(storage_root / security_test_data["account_a"].id, ignore_errors=True)
