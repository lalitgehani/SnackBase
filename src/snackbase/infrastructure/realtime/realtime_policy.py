"""Per-subscriber authorization for realtime delivery.

``broadcast_to_account`` used to filter on two things: the connection's
``account_id`` and whether a subscription named the collection and operation.
The record was then forwarded verbatim. The tenant boundary held, but realtime
was a second read path *inside* a tenant that answered to none of the controls
the REST read path applies — so a user who could not list a row, or who was
projected down to a subset of fields, or whose PII was masked, got the complete
row the moment they subscribed.

This policy is that missing half. It reuses the same pieces as the REST path:
``check_collection_permission`` for the view rule and field projection,
``apply_field_filter`` for the projection, and ``PIIMaskingService.mask_record``
for masking. Row visibility is answered by re-reading the row through the
compiled rule filter, so there is exactly one rule engine in the codebase and it
is the SQL one.

Broadcasts run as detached tasks, after the request that caused them has
finished, so the policy owns its own short-lived session.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import PIIMaskingService
from snackbase.infrastructure.api.dependencies import AuthorizationContext
from snackbase.infrastructure.api.middleware import apply_field_filter, check_collection_permission
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenType
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    RecordRepository,
    UserRepository,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class _Subscriber:
    """What the policy needs to know about the user behind a connection."""

    auth_context: AuthorizationContext
    groups: list[str]


class RealtimeReadPolicy:
    """Decides what, if anything, a subscriber may see of a broadcast record."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        """Initialize the policy.

        Args:
            session_factory: Callable returning a new session (an async
                sessionmaker). A broadcast outlives its originating request, so
                the policy cannot borrow that request's session.
        """
        self._session_factory = session_factory

    async def filter_for_subscriber(
        self,
        *,
        collection: str,
        account_id: str,
        user_id: str,
        operation: str,
        data: Any,
    ) -> Any | None:
        """Return what this subscriber may receive, or None to deliver nothing.

        Args:
            collection: Collection the event belongs to.
            account_id: Account the event belongs to (already matched by the
                caller against the connection).
            user_id: The subscriber's user ID.
            operation: ``create``, ``update`` or ``delete``.
            data: The record payload as published.

        Returns:
            The payload to deliver, or None if the subscriber may not see it.
            Errors resolve to None: an event that cannot be authorized is not
            delivered.
        """
        if not isinstance(data, dict):
            # Nothing to project or mask, and nothing to check a rule against.
            return None

        record_id = data.get("id")
        if not record_id:
            return None

        try:
            async with self._session_factory() as session:
                return await self._filter(
                    session=session,
                    collection=collection,
                    account_id=account_id,
                    user_id=user_id,
                    operation=operation,
                    data=data,
                )
        except HTTPException:
            # The ordinary "denied" answer from check_collection_permission:
            # locked operation, no rules, or a rule needing more context.
            logger.debug(
                "Realtime event withheld: subscriber may not read this collection",
                collection=collection,
                user_id=user_id,
            )
            return None
        except Exception as e:  # fail closed: no event is better than a leak
            logger.error(
                "Realtime authorization failed; event withheld",
                collection=collection,
                account_id=account_id,
                user_id=user_id,
                operation=operation,
                error=str(e),
            )
            return None

    async def _filter(
        self,
        *,
        session: AsyncSession,
        collection: str,
        account_id: str,
        user_id: str,
        operation: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        subscriber = await self._load_subscriber(session, account_id, user_id)
        if subscriber is None:
            return None

        rule_filter = await check_collection_permission(
            auth_context=subscriber.auth_context,
            collection=collection,
            operation="view",
            session=session,
            record=data,
        )

        schema = await self._load_schema(session, collection)
        if schema is None:
            return None

        if operation == "delete":
            # The row is gone, so its visibility can no longer be established.
            # Subscribers are told an id disappeared and nothing more.
            return {"id": data["id"]}

        visible = await RecordRepository(session).get_by_id(
            collection_name=collection,
            record_id=str(data["id"]),
            account_id=account_id,
            schema=schema,
            rule_filter=rule_filter,
        )
        if visible is None:
            # The row exists (it was just written) but this subscriber's view
            # rule excludes it — exactly the REST answer.
            return None

        projected = apply_field_filter(data, rule_filter.allowed_fields)
        return PIIMaskingService.mask_record(
            projected, schema, subscriber.groups, account_id
        )

    async def _load_subscriber(
        self, session: AsyncSession, account_id: str, user_id: str
    ) -> _Subscriber | None:
        """Build the subscriber's authorization context from the database.

        Read fresh rather than trusted from the connection's token: a long-lived
        subscription must not outlive a role or group change.
        """
        user = await UserRepository(session).get_by_id_with_groups(user_id)
        if user is None or not user.is_active or user.account_id != account_id:
            return None

        groups = [group.name for group in user.groups]
        auth_user = AuthenticatedUser(
            user_id=user.id,
            account_id=user.account_id,
            email=user.email,
            role=str(user.role_id),
            token_type=TokenType.JWT,
            groups=groups,
        )
        return _Subscriber(
            auth_context=AuthorizationContext(
                user=auth_user, role_id=int(user.role_id), scopes=None
            ),
            groups=groups,
        )

    async def _load_schema(
        self, session: AsyncSession, collection: str
    ) -> list[dict[str, Any]] | None:
        model = await CollectionRepository(session).get_by_name(collection)
        if model is None:
            return None
        try:
            schema = json.loads(model.schema)
        except (json.JSONDecodeError, TypeError):
            return None
        return schema if isinstance(schema, list) else None
