"""SSRF-WH-*: webhook URL-validation guards (H-01).

``validate_webhook_url`` blocks a hand-written list of private networks. Three
things are missing from it:

* **Link-local (169.254.0.0/16)** — the cloud instance-metadata range, the
  single most valuable SSRF target, is absent. So is ``0.0.0.0/8``.
* **IPv4-mapped IPv6** — ``::ffff:127.0.0.1`` parses as an ``IPv6Address``, and
  comparing it against the IPv4 networks in the deny list silently yields
  ``False`` rather than raising.
* **DNS resolution** — only literal IPs are checked. A hostname that resolves
  to a private address passes untouched.

``test_webhook`` then compounds it: it performs no re-validation and reflects
up to 5000 characters of the response body straight back to the caller, which
turns a blind SSRF into a read primitive.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.webhook import WebhookModel
from snackbase.infrastructure.webhooks.webhook_service import (
    generate_webhook_secret,
    validate_webhook_url,
)
from tests.security.helpers import assert_no_leak

METADATA_MARKER = "AWS-METADATA-CREDENTIALS"
METADATA_URL = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit level — the deny list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/hook",
        "http://10.0.0.1/hook",
        "http://172.16.0.1/hook",
        "http://192.168.1.1/hook",
        "http://[::1]/hook",
        "http://[fc00::1]/hook",
    ],
)
def test_ssrf_wh_001_known_private_ranges_are_rejected(url: str) -> None:
    """SSRF-WH-001: regression — the ranges already on the deny list stay blocked."""
    with pytest.raises(ValueError, match="private/loopback"):
        validate_webhook_url(url, require_https=False)


@pytest.mark.parametrize(
    "url",
    [
        # Cloud instance metadata — the highest-value SSRF target.
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.170.2/v2/credentials",
        # "This host", routed to loopback on Linux.
        "http://0.0.0.0/hook",
    ],
)
@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
def test_ssrf_wh_002_link_local_and_unspecified_are_rejected(url: str) -> None:
    """SSRF-WH-002: link-local and 0.0.0.0/8 must be on the deny list."""
    with pytest.raises(ValueError, match="private/loopback"):
        validate_webhook_url(url, require_https=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://[::ffff:127.0.0.1]/hook",
        "http://[::ffff:169.254.169.254]/hook",
        "http://[::ffff:10.0.0.1]/hook",
    ],
)
@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
def test_ssrf_wh_003_ipv4_mapped_ipv6_is_rejected(url: str) -> None:
    """SSRF-WH-003: an IPv4-mapped IPv6 literal must not slip past the deny list."""
    with pytest.raises(ValueError, match="private/loopback"):
        validate_webhook_url(url, require_https=False)


@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
def test_ssrf_wh_004_hostname_resolving_to_private_ip_is_rejected() -> None:
    """SSRF-WH-004: the hostname must be resolved before the deny list is applied."""
    # `localhost` resolves to 127.0.0.1 on every supported platform, so it needs
    # no network access to demonstrate the missing resolution step.
    with pytest.raises(ValueError):
        validate_webhook_url("http://localhost/hook", require_https=False)


def test_ssrf_wh_005_public_https_url_still_accepted() -> None:
    """SSRF-WH-005: positive control — a real external HTTPS URL still validates."""
    validate_webhook_url("https://hooks.example.com/inbound", require_https=True)


def test_ssrf_wh_006_non_http_scheme_rejected() -> None:
    """SSRF-WH-006: regression — non-HTTP schemes stay rejected."""
    with pytest.raises(ValueError, match="scheme"):
        validate_webhook_url("file:///etc/passwd", require_https=False)


# ---------------------------------------------------------------------------
# Integration level — creation and the test endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
async def test_ssrf_wh_010_cannot_create_webhook_pointing_at_metadata(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """SSRF-WH-010: creating a metadata-targeted webhook must be refused."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": METADATA_URL,
            "collection": "posts",
            "events": ["create"],
        },
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
@respx.mock
async def test_ssrf_wh_011_test_endpoint_does_not_reflect_internal_body(
    client: AsyncClient,
    db_session: AsyncSession,
    security_test_data: dict[str, Any],
) -> None:
    """SSRF-WH-011: `POST /webhooks/{id}/test` must not echo an internal response.

    The webhook row is inserted directly so this stays independent of whether
    the creation-time deny list has been fixed yet.
    """
    respx.post(METADATA_URL).mock(
        return_value=httpx.Response(200, text=METADATA_MARKER)
    )

    webhook = WebhookModel(
        id=str(uuid.uuid4()),
        account_id=security_test_data["account_a"].id,
        url=METADATA_URL,
        collection="posts",
        events=["create"],
        secret=generate_webhook_secret(),
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(webhook)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/webhooks/{webhook.id}/test",
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert response.json().get("success") is not True, response.text
    assert_no_leak(response, METADATA_MARKER)
