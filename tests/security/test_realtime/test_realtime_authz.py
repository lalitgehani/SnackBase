"""RT-*: realtime authorization and payload-filtering guards (M-01).

``ConnectionManager.broadcast_to_account`` filters on exactly two things: the
connection's ``account_id`` and whether a subscription names the collection and
operation. The record payload is forwarded verbatim — the code even carries a
``TODO: Integrate with permission system for granular field-level checks``.

That makes the cross-tenant boundary sound but leaves realtime a second,
unguarded read path *inside* a tenant. A user who cannot list a row over REST,
or who is projected down to a subset of fields, or whose PII is masked, gets
the complete row the moment they subscribe.

These tests drive the manager directly rather than over a WebSocket: the
filtering decision lives in ``broadcast_to_account``, and asserting on the
delivered payload there is both precise and deterministic.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from snackbase.infrastructure.realtime.realtime_manager import (
    ConnectionManager,
    RealtimeConnection,
    Subscription,
)

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


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-01 fix pending", strict=True)
async def test_rt_010_restricted_user_does_not_receive_unreadable_rows(
    manager: ConnectionManager,
) -> None:
    """RT-010: a row the view rule excludes must not be delivered."""
    subscriber = RecordingConnection(user_id="user-restricted", account_id="AB1111")
    subscriber.subscribe()
    await manager.add_connection(subscriber)

    # The subscriber's collection rule is `owner_id = @request.auth.id`, so this
    # row is invisible to them over REST.
    await manager.broadcast_to_account(
        account_id="AB1111",
        collection=COLLECTION,
        operation="create",
        data=FORBIDDEN_RECORD,
    )

    assert subscriber.received == [], (
        "subscriber received a row its collection view rule excludes"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-01 fix pending", strict=True)
async def test_rt_011_fields_outside_projection_are_stripped(
    manager: ConnectionManager,
) -> None:
    """RT-011: fields outside the subscriber's projection must not be delivered."""
    subscriber = RecordingConnection(user_id="user-restricted", account_id="AB1111")
    subscriber.subscribe()
    await manager.add_connection(subscriber)

    # view_fields is "id,title" for this user; `salary` is outside it.
    await manager.broadcast_to_account(
        account_id="AB1111",
        collection=COLLECTION,
        operation="create",
        data=ALLOWED_RECORD,
    )

    assert subscriber.payloads, "positive control: the allowed row was not delivered"
    assert "salary" not in subscriber.payloads[0], (
        "a field outside the subscriber's projection was delivered"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-01 fix pending", strict=True)
async def test_rt_012_pii_fields_are_masked_in_delivered_events(
    manager: ConnectionManager,
) -> None:
    """RT-012: PII must be masked in realtime exactly as it is over REST."""
    subscriber = RecordingConnection(user_id="user-restricted", account_id="AB1111")
    subscriber.subscribe()
    await manager.add_connection(subscriber)

    await manager.broadcast_to_account(
        account_id="AB1111",
        collection=COLLECTION,
        operation="create",
        data=ALLOWED_RECORD,
    )

    assert subscriber.payloads, "positive control: the allowed row was not delivered"
    assert subscriber.payloads[0].get("ssn") != ALLOWED_RECORD["ssn"], (
        "an unmasked PII field was delivered over realtime"
    )
