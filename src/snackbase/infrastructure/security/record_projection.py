"""Project a record for delivery to an external sink on behalf of a principal.

Automation (API-defined hooks, outbound webhooks) receives record events from
the persistence layer, where the payload is the full stored row. Anything an
automation forwards leaves the server, so it must see no more of the row than
its author could read through ``GET /{collection}/{id}``: the author's ``view``
rule decides whether the row is visible at all, ``allowed_fields`` projects it,
encrypted fields are redacted, and PII is masked for the author's groups.

The event fires inside the writing transaction, before commit, and a delete
event describes a row that no longer exists, so visibility cannot be answered
by re-reading the row. Instead the compiled view rule is evaluated against the
event's own values, bound into a one-row CTE whose column names come from the
collection schema (never from the payload).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snackbase.core.logging import get_logger
from snackbase.domain.services import PIIMaskingService
from snackbase.domain.services.collection_validator import NAME_PATTERN
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID, AuthorizationContext
from snackbase.infrastructure.api.middleware import (
    RuleFilter,
    apply_field_filter,
    check_collection_permission,
)
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenType
from snackbase.infrastructure.persistence.models import UserModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository
from snackbase.infrastructure.security.field_encryption import redact_record_for_response

logger = get_logger(__name__)

_SYSTEM_COLUMNS = ("id", "account_id", "created_at", "updated_at", "created_by", "updated_by")

_SQL_TYPES = {"number": "NUMERIC", "boolean": "BOOLEAN"}


async def project_record_for_user(
    session: AsyncSession,
    *,
    collection: str,
    account_id: str,
    user_id: str | None,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the part of ``record`` that ``user_id`` may read, or None.

    Args:
        session: Database session used for rule resolution and evaluation.
        collection: Collection the record belongs to.
        account_id: Account the record belongs to.
        user_id: The principal whose read access governs the projection
            (the automation's author). ``None`` resolves to no access.
        record: The record values as emitted by the record event.

    Returns:
        The projected record, or None if the principal may not view it. Every
        error resolves to None: a record that cannot be authorized is withheld.
    """
    if not user_id:
        return None

    try:
        auth_context, groups = await _load_principal(session, account_id, user_id)
        if auth_context is None or auth_context.user is None:
            return None
        principal_account_id = auth_context.user.account_id

        try:
            rule = await check_collection_permission(
                auth_context=auth_context,
                collection=collection,
                operation="view",
                session=session,
            )
        except HTTPException:
            return None

        schema = await _load_schema(session, collection)
        if schema is None:
            return None

        if rule.sql.strip() != "1=1" and not await _satisfies_rule(
            session, rule, record, schema
        ):
            return None

        projected = dict(record)
        if rule.allowed_fields != "*":
            projected = apply_field_filter(projected, rule.allowed_fields)
        projected = redact_record_for_response(projected, schema)
        return PIIMaskingService.mask_record(projected, schema, groups, principal_account_id)
    except Exception as exc:  # fail closed
        logger.error(
            "Record projection failed; record withheld",
            collection=collection,
            account_id=account_id,
            user_id=user_id,
            error=str(exc),
        )
        return None


async def _load_principal(
    session: AsyncSession, account_id: str, user_id: str
) -> tuple[AuthorizationContext | None, list[str]]:
    """Build the principal's authorization context from current database state."""
    user = (
        await session.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.groups), selectinload(UserModel.role))
        )
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None, []
    if user.account_id not in (account_id, SYSTEM_ACCOUNT_ID):
        return None, []

    groups = [group.name for group in user.groups]
    auth_user = AuthenticatedUser(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role=user.role.name if user.role else "",
        token_type=TokenType.JWT,
        groups=groups,
    )
    return AuthorizationContext(user=auth_user, role_id=user.role_id, scopes=None), groups


async def _load_schema(session: AsyncSession, collection: str) -> list[dict[str, Any]] | None:
    model = await CollectionRepository(session).get_by_name(collection)
    if model is None:
        return None
    try:
        schema = json.loads(model.schema)
    except (json.JSONDecodeError, TypeError):
        return None
    return schema if isinstance(schema, list) else None


def _bind_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


async def _satisfies_rule(
    session: AsyncSession,
    rule: RuleFilter,
    record: dict[str, Any],
    schema: list[dict[str, Any]],
) -> bool:
    """Evaluate a compiled row rule against the record's own values."""
    columns: list[tuple[str, str]] = [(name, "TEXT") for name in _SYSTEM_COLUMNS]
    for field in schema:
        name = field.get("name")
        field_type = str(field.get("type", "text")).lower()
        if not isinstance(name, str) or not NAME_PATTERN.match(name):
            continue
        if field_type == "computed" or name in _SYSTEM_COLUMNS:
            continue
        columns.append((name, _SQL_TYPES.get(field_type, "TEXT")))

    select_parts = []
    params: dict[str, Any] = {}
    for index, (name, sql_type) in enumerate(columns):
        param = f"proj_col_{index}"
        select_parts.append(f'CAST(:{param} AS {sql_type}) AS "{name}"')
        params[param] = _bind_value(record.get(name))
    params.update(rule.params)

    check_sql = (
        f"WITH r AS (SELECT {', '.join(select_parts)}) "
        f"SELECT 1 FROM r WHERE ({rule.sql})"
    )
    result = await session.execute(text(check_sql), params)
    return result.scalar() is not None
