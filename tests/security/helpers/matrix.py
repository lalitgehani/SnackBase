"""Attack-matrix helper for cross-tenant isolation tests.

Runs the standard "Account B attacks a resource owned by Account A" matrix
over a single URL so each surface (records, endpoints, functions, files) can
be checked with the same discipline instead of hand-rolled per-test loops.
"""

from __future__ import annotations

from typing import Any

# Key used for the owner's positive-control request in the returned dict.
OWNER_CONTROL_KEY = "OWNER"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def cross_tenant_matrix(
    attack_client: Any,
    *,
    victim_url: str,
    victim_token: str,
    attacker_token: str,
    write_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an A→B cross-tenant attack matrix against a victim-owned URL.

    Args:
        attack_client: The ``AttackClient`` wrapper, so every request is logged
            into the consolidated HTML security report.
        victim_url: URL of a resource owned by the victim account.
        victim_token: The victim's token, used only for the positive control
            that proves the resource is genuinely reachable by its owner.
        attacker_token: The attacker's token from a different account.
        write_body: When given, a POST with this body is added to the matrix.

    Returns:
        A dict mapping ``"GET"``/``"PATCH"``/``"DELETE"`` (and ``"POST"`` when
        ``write_body`` is given) to the attacker's response, plus
        ``OWNER_CONTROL_KEY`` mapped to the owner's control GET.
    """
    results: dict[str, Any] = {}

    results[OWNER_CONTROL_KEY] = await attack_client.get(
        victim_url,
        headers=_auth(victim_token),
        description=f"Owner control GET {victim_url}",
    )

    results["GET"] = await attack_client.get(
        victim_url,
        headers=_auth(attacker_token),
        description=f"Cross-tenant GET {victim_url}",
    )

    results["PATCH"] = await attack_client.patch(
        victim_url,
        json=write_body if write_body is not None else {},
        headers=_auth(attacker_token),
        description=f"Cross-tenant PATCH {victim_url}",
    )

    if write_body is not None:
        results["POST"] = await attack_client.post(
            victim_url,
            json=write_body,
            headers=_auth(attacker_token),
            description=f"Cross-tenant POST {victim_url}",
        )

    # DELETE runs last so the earlier probes are not invalidated by removal.
    results["DELETE"] = await attack_client.delete(
        victim_url,
        headers=_auth(attacker_token),
        description=f"Cross-tenant DELETE {victim_url}",
    )

    return results
