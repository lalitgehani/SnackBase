"""Long-work job helper for function handlers."""

from __future__ import annotations

from typing import Any

from snackbase_fn.client import get_admin_client, get_client


def enqueue_job(
    name: str,
    payload: dict[str, Any] | None = None,
    *,
    use_admin: bool = False,
) -> dict[str, Any]:
    """Enqueue a background job via the SnackBase Jobs API.

    Returns the parsed JSON response body from the jobs API.
    """
    client = get_admin_client() if use_admin else get_client()
    try:
        response = client.post(
            "/api/v1/admin/jobs",
            json={"name": name, "payload": payload or {}},
        )
        response.raise_for_status()
        return response.json()
    finally:
        client.close()
