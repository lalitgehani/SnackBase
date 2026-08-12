"""RT-*: realtime authorization and payload-filtering guards (M-01).

``ConnectionManager.broadcast_to_account`` used to filter on exactly two things:
the connection's ``account_id`` and whether a subscription named the collection
and operation. The record payload was then forwarded verbatim — the code carried
a ``TODO: Integrate with permission system for granular field-level checks``.

That kept the cross-tenant boundary sound but left realtime a second, unguarded
read path *inside* a tenant. A user who could not list a row over REST, or who
was projected down to a subset of fields, or whose PII was masked, got the
complete row the moment they subscribed.

RT-001/002 drive a bare manager: subscription and tenant matching is all they
are about. RT-010/011/012 need the real thing — a collection with real rules and
rows in it — because the answer they check is the rule engine's. They construct
the manager with the production ``RealtimeReadPolicy`` over the test session, so
the assertions are about the shipped decision and not a stand-in for it. (As
first written they drove a bare ``ConnectionManager()`` with no rule source at
all, and asserted view-rule and projection behaviour it had no way to know
about; F4.1 specified exercising this "via httpx/ASGI transport" against real
payloads, which is what happens here.)
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import RoleModel, UserModel
from snackbase.infrastructure.realtime.realtime_manager import (
    ConnectionManager,
    RealtimeConnection,
    Subscription,
)
from snackbase.infrastructure.realtime.realtime_policy import RealtimeReadPolicy

COLLECTION = "invoices"

ALLOWED_RECORD = {
    "id": "rec-owned",
    "title": "Owned by the subscriber",
    "owner_id": "user-restricted",
    "salary": 120000,
    "ssn": "123-45-6789",
}
FORBIDDEN_RECORD = {
    "id": "rec-someone-else",
    "title": "Not visible to the subscriber",
    "owner_id": "user-other",
    "salary": 250000,
    "ssn": "987-65-4321",
}

SUBSCRIBER_SSN = "123-45-6789"
PEER_SSN = "987-65-4321"


class RecordingConnection(RealtimeConnection):
    """A connection that captures delivered events instead of sending them."""

    def __init__(self, *, user_id: str, account_id: str) -> None:
        self.received: list[Any] = []

        async def _capture(data: Any) -> None:
            self.received.append(data)

        super().__init__(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            account_id=account_id,
            send_callback=_capture,
        )

    def subscribe(self, collection: str = COLLECTION) -> None:
        self.add_subscription(
            Subscription(
                id=str(uuid.uuid4()),
                collection=collection,
                account_id=self.account_id,
                user_id=self.user_id,
            )
        )

    @property
    def payloads(self) -> list[Any]:
        return [event["data"] for event in self.received]


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _session_factory(session: AsyncSession) -> Callable[[], Any]:
    """Hand the policy the test's session under the interface it expects.

    In production the policy opens its own session per broadcast, because a
    broadcast outlives the request that caused it. Here the one test session has
    to be reused, so it is wrapped in a context manager that does not close it.
    """

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncSession]:
        yield session

    return factory


# ---------------------------------------------------------------------------
# Cross-tenant — already enforced, locked in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rt_001_subscriber_receives_no_cross_account_events(
    manager: ConnectionManager,
) -> None:
    """RT-001: a subscriber in B receives nothing from an A-scoped mutation."""
    subscriber_a = RecordingConnection(user_id="user-a", account_id="AB1111")
    subscriber_b = RecordingConnection(user_id="user-b", account_id="AB2222")
    subscriber_a.subscribe()
    subscriber_b.subscribe()
    await manager.add_connection(subscriber_a)
    await manager.add_connection(subscriber_b)

    await manager.broadcast_to_account(
        account_id="AB1111",
        collection=COLLECTION,
        operation="create",
        data=ALLOWED_RECORD,
    )

    assert len(subscriber_a.received) == 1
    assert subscriber_b.received == []


@pytest.mark.asyncio
async def test_rt_002_unsubscribed_collection_delivers_nothing(
    manager: ConnectionManager,
) -> None:
    """RT-002: regression — events only reach subscriptions that named them."""
    subscriber = RecordingConnection(user_id="user-a", account_id="AB1111")
    subscriber.subscribe(collection="other_collection")
    await manager.add_connection(subscriber)

    await manager.broadcast_to_account(
        account_id="AB1111",
        collection=COLLECTION,
        operation="create",
        data=ALLOWED_RECORD,
    )

    assert subscriber.received == []


# ---------------------------------------------------------------------------
# Intra-tenant — the gap
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def restricted_realtime(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
    security_test_data: dict[str, Any],
) -> Any:
    """A collection the subscriber sees only part of, plus a manager wired to it.

    * view rule ``created_by = @request.auth.id`` — the subscriber may read only
      its own rows;
    * view projection ``id,title,ssn`` — ``salary`` is outside it;
    * ``ssn`` is a PII field and the subscriber is in no group, so it masks.

    Yields the wired ``manager``, the subscriber's ``connection``, and the two
    records: one the subscriber owns and one a peer owns.
    """
    account_a = security_test_data["account_a"]
    subscriber = security_test_data["user_a"]
    subscriber_token = security_test_data["user_a_token"]

    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    peer = UserModel(
        id=str(uuid.uuid4()),
        email=f"rt_peer_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_a.id,
        password_hash="hashed_secret",
        role_id=user_role.id,
        is_active=True,
    )
    db_session.add(peer)
    await db_session.commit()
    peer_token = jwt_service.create_access_token(
        user_id=peer.id, account_id=peer.account_id, email=peer.email, role="user"
    )

    collection = f"rt_{uuid.uuid4().hex[:8]}"
    admin_headers = _auth(superadmin_token)

    created = await client.post(
        "/api/v1/collections",
        json={
            "name": collection,
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "salary", "type": "number"},
                {"name": "ssn", "type": "text", "pii": True, "mask_type": "ssn"},
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text

    rules = await client.put(
        f"/api/v1/collections/{collection}/rules",
        json={
            "list_rule": "created_by = @request.auth.id",
            "view_rule": "created_by = @request.auth.id",
            "create_rule": "",
            "view_fields": json.dumps(["id", "title", "ssn"]),
        },
        headers=admin_headers,
    )
    assert rules.status_code == 200, rules.text

    owned = await client.post(
        f"/api/v1/records/{collection}",
        json={"title": "Owned by the subscriber", "salary": 120000, "ssn": SUBSCRIBER_SSN},
        headers=_auth(subscriber_token),
    )
    assert owned.status_code == 201, owned.text

    forbidden = await client.post(
        f"/api/v1/records/{collection}",
        json={"title": "Not visible to the subscriber", "salary": 250000, "ssn": PEER_SSN},
        headers=_auth(peer_token),
    )
    assert forbidden.status_code == 201, forbidden.text

    connection = RecordingConnection(user_id=subscriber.id, account_id=account_a.id)
    connection.subscribe(collection=collection)
    manager = ConnectionManager(policy=RealtimeReadPolicy(_session_factory(db_session)))
    await manager.add_connection(connection)

    async def broadcast(record: dict[str, Any], operation: str = "create") -> None:
        await manager.broadcast_to_account(
            account_id=account_a.id,
            collection=collection,
            operation=operation,
            data=record,
        )

    yield {
        "collection": collection,
        "connection": connection,
        "broadcast": broadcast,
        "owned_record": {**owned.json(), "salary": 120000, "ssn": SUBSCRIBER_SSN},
        "forbidden_record": {**forbidden.json(), "salary": 250000, "ssn": PEER_SSN},
    }


@pytest.mark.asyncio
async def test_rt_010_restricted_user_does_not_receive_unreadable_rows(
    restricted_realtime: dict[str, Any],
) -> None:
    """RT-010: a row the view rule excludes must not be delivered."""
    connection = restricted_realtime["connection"]

    # The subscriber's view rule is `created_by = @request.auth.id`, and a peer
    # created this row, so it is invisible to them over REST.
    await restricted_realtime["broadcast"](restricted_realtime["forbidden_record"])

    assert connection.received == [], (
        "subscriber received a row its collection view rule excludes"
    )


@pytest.mark.asyncio
async def test_rt_011_fields_outside_projection_are_stripped(
    restricted_realtime: dict[str, Any],
) -> None:
    """RT-011: fields outside the subscriber's projection must not be delivered."""
    connection = restricted_realtime["connection"]

    # view_fields is "id,title,ssn" for this collection; `salary` is outside it.
    await restricted_realtime["broadcast"](restricted_realtime["owned_record"])

    assert connection.payloads, "positive control: the allowed row was not delivered"
    assert "salary" not in connection.payloads[0], (
        "a field outside the subscriber's projection was delivered"
    )


@pytest.mark.asyncio
async def test_rt_012_pii_fields_are_masked_in_delivered_events(
    restricted_realtime: dict[str, Any],
) -> None:
    """RT-012: PII must be masked in realtime exactly as it is over REST."""
    connection = restricted_realtime["connection"]

    await restricted_realtime["broadcast"](restricted_realtime["owned_record"])

    assert connection.payloads, "positive control: the allowed row was not delivered"
    assert connection.payloads[0].get("ssn") != SUBSCRIBER_SSN, (
        "an unmasked PII field was delivered over realtime"
    )


@pytest.mark.asyncio
async def test_rt_013_delete_events_carry_only_the_id(
    restricted_realtime: dict[str, Any],
) -> None:
    """RT-013: a delete cannot be re-checked, so it delivers nothing but the id.

    The row is already gone when the event goes out, so its visibility can no
    longer be established. Withholding every field but the id keeps the
    subscription usable (a client knows to drop the row) without turning delete
    into a way to read fields the view rule or the projection would have hidden.
    """
    connection = restricted_realtime["connection"]

    await restricted_realtime["broadcast"](
        restricted_realtime["owned_record"], operation="delete"
    )

    assert connection.payloads, "positive control: the delete was not delivered"
    assert connection.payloads[0] == {"id": restricted_realtime["owned_record"]["id"]}
