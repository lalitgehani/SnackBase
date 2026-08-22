"""RATE-LOGIN-*: online password-guessing guards (H-02).

Three independent gaps once left `/api/v1/auth/login` unlimited:

* **No lockout.** Failed logins were logged and nothing else — no counter per
  ``(email, account)``, so an attacker got unlimited attempts against a single
  victim regardless of any IP-based limit.
* **Rate limiting was off by default.** ``rate_limit_enabled`` defaulted to
  ``False``, so ``RateLimitMiddleware`` returned immediately and no endpoint —
  auth included — was throttled unless an operator opted in.
* **One bucket behind a proxy.** The key came purely from
  ``request.client.host``, so every client behind a reverse proxy collapsed onto
  the proxy's address.

These run against the *default* configuration on purpose: "you must set an env
var first" is exactly the state H-02 flagged. RATE-LOGIN-001..005 exercise the
per-IP throttle; 010/011 exercise the per-account lockout, which is the layer
that survives an attacker rotating source addresses.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from snackbase.core.config import Settings, get_settings
from snackbase.infrastructure.api.middleware.client_ip import get_client_ip
from snackbase.infrastructure.auth import hash_password
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

# Comfortably above any plausible threshold, small enough to stay fast.
BURST_ATTEMPTS = 25


def _fake_request(peer: str, headers: dict[str, str]) -> Any:
    """The smallest thing `get_client_ip` needs: a peer address and headers."""
    return SimpleNamespace(
        client=SimpleNamespace(host=peer),
        headers=Headers(headers),
    )


@pytest_asyncio.fixture
async def bruteforce_user(db_session: AsyncSession) -> dict[str, Any]:
    """A password-auth user with a known good password."""
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()

    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="BF0001",
        name="Bruteforce Test Account",
        slug=f"bruteforce-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(account)

    password = "CorrectHorseBattery1!"
    user = UserModel(
        id=str(uuid.uuid4()),
        email=f"bf-{uuid.uuid4().hex[:6]}@example.com",
        account_id=account.id,
        password_hash=hash_password(password),
        role_id=user_role.id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "email": user.email,
        "password": password,
        "account": account.account_code,
        "account_id": account.id,
        "user_id": user.id,
    }


async def _failed_logins(
    client: AsyncClient, user: dict[str, Any], count: int, **kwargs: Any
) -> list[int]:
    statuses: list[int] = []
    for attempt in range(count):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": user["email"],
                "password": f"wrong-password-{attempt}",
                "account": user["account"],
            },
            **kwargs,
        )
        statuses.append(response.status_code)
    return statuses


@pytest.mark.asyncio
async def test_rate_login_001_repeated_failures_are_throttled(
    client: AsyncClient, bruteforce_user: dict[str, Any]
) -> None:
    """RATE-LOGIN-001: a burst of failed logins must stop returning plain 401."""
    statuses = await _failed_logins(client, bruteforce_user, BURST_ATTEMPTS)

    assert any(code != status.HTTP_401_UNAUTHORIZED for code in statuses), (
        f"all {BURST_ATTEMPTS} failed logins returned 401 — guessing is unlimited"
    )


@pytest.mark.asyncio
async def test_rate_login_002_correct_password_refused_during_lockout(
    client: AsyncClient, bruteforce_user: dict[str, Any]
) -> None:
    """RATE-LOGIN-002: the lockout must hold even for the correct password."""
    await _failed_logins(client, bruteforce_user, BURST_ATTEMPTS)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": bruteforce_user["email"],
            "password": bruteforce_user["password"],
            "account": bruteforce_user["account"],
        },
    )

    assert response.status_code != status.HTTP_200_OK, (
        "correct password succeeded immediately after a failed-login burst"
    )


def test_rate_login_003_rate_limiting_enabled_by_default() -> None:
    """RATE-LOGIN-003: throttling must be on out of the box, not opt-in."""
    assert Settings().rate_limit_enabled is True


@pytest.mark.asyncio
async def test_rate_login_004_superadmin_account_not_exempt_from_login_throttle(
    client: AsyncClient, superadmin_token: str, bruteforce_user: dict[str, Any]
) -> None:
    """RATE-LOGIN-004: a superadmin token must not buy an exemption at login.

    ``RateLimitMiddleware`` returns early for the system account. Login is
    unauthenticated, but a caller can present a superadmin bearer token
    alongside the login body and take that early-return path.
    """
    statuses = await _failed_logins(
        client,
        bruteforce_user,
        BURST_ATTEMPTS,
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert any(code != status.HTTP_401_UNAUTHORIZED for code in statuses), (
        "a superadmin token exempted the caller from the login throttle"
    )


@pytest.mark.asyncio
async def test_rate_login_005_forwarded_for_distinguishes_proxied_clients(
    client: AsyncClient, bruteforce_user: dict[str, Any]
) -> None:
    """RATE-LOGIN-005: proxied clients must not share one rate-limit bucket.

    Two distinct `X-Forwarded-For` values arriving from the same proxy IP must
    be tracked separately, otherwise the limit is either useless (shared quota)
    or a denial-of-service against every client behind the proxy.
    """
    exhausted = await _failed_logins(
        client,
        bruteforce_user,
        BURST_ATTEMPTS,
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert any(code != status.HTTP_401_UNAUTHORIZED for code in exhausted), (
        "the first client was never throttled, so per-client tracking is untestable"
    )

    other_client = await _failed_logins(
        client,
        bruteforce_user,
        1,
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert other_client == [status.HTTP_401_UNAUTHORIZED], (
        "a different forwarded client inherited the first client's throttle"
    )


@pytest.mark.asyncio
async def test_rate_login_010_distributed_guessing_locks_the_account(
    client: AsyncClient, bruteforce_user: dict[str, Any], db_session: AsyncSession
) -> None:
    """RATE-LOGIN-010: rotating source addresses must still hit the account lockout.

    RATE-LOGIN-001..005 are all satisfied by the per-IP throttle alone. An
    attacker with a pool of addresses pays that toll once per address, so the
    per-account counter is the layer that actually bounds guessing against a
    chosen victim — and it is the layer with no other coverage.
    """
    settings = get_settings()
    attempts = settings.login_lockout_threshold

    for attempt in range(attempts):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": bruteforce_user["email"],
                "password": f"wrong-{attempt}",
                "account": bruteforce_user["account"],
            },
            # A fresh address each time, so the per-IP budget is never spent.
            headers={"X-Forwarded-For": f"198.51.100.{attempt + 1}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.id == bruteforce_user["user_id"])
        )
    ).scalar_one()
    await db_session.refresh(user)
    assert user.failed_login_attempts >= attempts
    assert user.locked_until is not None, "the account never locked"

    # The correct password must not open a locked account, from any address.
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": bruteforce_user["email"],
            "password": bruteforce_user["password"],
            "account": bruteforce_user["account"],
        },
        headers={"X-Forwarded-For": "198.51.100.250"},
    )
    assert response.status_code != status.HTTP_200_OK, (
        "the correct password opened a locked account"
    )


@pytest.mark.asyncio
async def test_rate_login_011_successful_login_clears_the_counter(
    client: AsyncClient, bruteforce_user: dict[str, Any], db_session: AsyncSession
) -> None:
    """RATE-LOGIN-011: a mistyped password must not accumulate towards a lockout forever."""
    await _failed_logins(client, bruteforce_user, 3)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": bruteforce_user["email"],
            "password": bruteforce_user["password"],
            "account": bruteforce_user["account"],
        },
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.id == bruteforce_user["user_id"])
        )
    ).scalar_one()
    await db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_rate_login_012_forwarded_for_ignored_from_untrusted_peer() -> None:
    """RATE-LOGIN-012: only a trusted proxy's `X-Forwarded-For` may be believed.

    Believing it unconditionally would let any client mint a fresh rate-limit
    bucket per request simply by varying the header.
    """
    forged = _fake_request("203.0.113.77", {"X-Forwarded-For": "8.8.8.8"})
    assert get_client_ip(forged) == "203.0.113.77"

    proxied = _fake_request("127.0.0.1", {"X-Forwarded-For": "8.8.8.8"})
    assert get_client_ip(proxied) == "8.8.8.8"


@pytest.mark.asyncio
async def test_rate_login_006_single_failure_returns_generic_401(
    client: AsyncClient, bruteforce_user: dict[str, Any]
) -> None:
    """RATE-LOGIN-006: regression — one failure still yields the generic 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": bruteforce_user["email"],
            "password": "definitely-wrong",
            "account": bruteforce_user["account"],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"] == "Authentication failed"
