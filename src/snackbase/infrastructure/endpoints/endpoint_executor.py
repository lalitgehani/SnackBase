"""Endpoint action executor for F8.2 Custom Endpoints.

Executes a list of actions for a custom endpoint invocation.
Extends the F8.1 action executor with:
  - Request context variables: request.body.*, request.query.*, request.params.*
  - Auth context variables: auth.user_id, auth.email, auth.account_id
  - Action chaining: actions[N].result
  - New action types: query_records, aggregate_records, transform

Template variables resolved in string values:
    {{request.body.field}}    — field from the request body (POST/PUT/PATCH)
    {{request.query.field}}   — URL query parameter
    {{request.params.field}}  — path parameter (from :param segments)
    {{auth.user_id}}          — authenticated user ID (empty if anonymous)
    {{auth.email}}            — authenticated user email
    {{auth.account_id}}       — account ID
    {{actions[N].result}}     — result of the Nth action (0-indexed)
    {{now}}                   — current UTC ISO timestamp

Shared action types (imported from F8.1 action_executor):
    send_webhook, send_email, create_record, update_record,
    delete_record, enqueue_job

New action types:
    query_records     — query records from a collection
    aggregate_records — aggregate records (count, sum, avg, group_by)
    transform         — reshape data using a template expression
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from snackbase.core.logging import get_logger

logger = get_logger(__name__)

# Maximum action execution depth to prevent infinite loops
_MAX_DEPTH = 5

# Template variable pattern: {{variable.path}} or {{actions[N].result}}
_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")

# Timeout for a full endpoint execution (seconds)
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class EndpointRequestContext:
    """Context available to action templates during endpoint execution.

    Attributes:
        request_body: Parsed JSON request body (POST/PUT/PATCH), or empty dict.
        request_query: URL query parameters as a flat string dict.
        request_params: Path parameters extracted from :param segments.
        auth_user_id: Authenticated user ID, or empty string for anonymous.
        auth_email: Authenticated user email, or empty string.
        auth_account_id: The account ID from authentication context.
        action_results: Running list of results from completed actions
            (populated during execution; used for {{actions[N].result}}).
    """

    request_body: dict[str, Any] = field(default_factory=dict)
    request_query: dict[str, str] = field(default_factory=dict)
    request_params: dict[str, str] = field(default_factory=dict)
    auth_user_id: str = ""
    auth_email: str = ""
    auth_account_id: str = ""
    action_results: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def _resolve_template(value: str, ctx: EndpointRequestContext) -> str:
    """Replace {{...}} placeholders in a string value."""
    now_str = datetime.now(UTC).isoformat()

    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        var = match.group(1).strip()

        if var == "now":
            return now_str

        if var.startswith("request.body."):
            key = var[len("request.body."):]
            val = ctx.request_body.get(key)
            return str(val) if val is not None else ""

        if var.startswith("request.query."):
            key = var[len("request.query."):]
            return ctx.request_query.get(key, "")

        if var.startswith("request.params."):
            key = var[len("request.params."):]
            return ctx.request_params.get(key, "")

        if var == "auth.user_id":
            return ctx.auth_user_id

        if var == "auth.email":
            return ctx.auth_email

        if var == "auth.account_id":
            return ctx.auth_account_id

        # actions[N].result
        actions_match = re.match(r"^actions\[(\d+)\]\.result$", var)
        if actions_match:
            idx = int(actions_match.group(1))
            if 0 <= idx < len(ctx.action_results):
                result = ctx.action_results[idx]
                if isinstance(result, (dict, list)):
                    import json
                    return json.dumps(result)
                return str(result) if result is not None else ""
            return ""

        # Unknown — leave as-is so config errors are visible
        return match.group(0)

    return _TEMPLATE_RE.sub(_replace, value)


def _resolve_value(value: Any, ctx: EndpointRequestContext) -> Any:
    """Recursively resolve template variables in dicts, lists, and strings."""
    if isinstance(value, str):
        return _resolve_template(value, ctx)
    if isinstance(value, dict):
        return {k: _resolve_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, ctx) for item in value]
    return value


def _resolve_action(action: dict[str, Any], ctx: EndpointRequestContext) -> dict[str, Any]:
    """Return a copy of the action with all template variables resolved."""
    return {k: _resolve_value(v, ctx) for k, v in action.items()}


# ---------------------------------------------------------------------------
# Shared action executors (delegates to F8.1 where possible)
# ---------------------------------------------------------------------------


async def _execute_send_webhook(config: dict[str, Any]) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_send_webhook as _fw
    await _fw(config)
    return None


async def _execute_send_email(config: dict[str, Any], session_factory: Any) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_send_email as _fe
    await _fe(config, session_factory)
    return None


async def _execute_create_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
    depth: int,
) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_create_record as _fc
    await _fc(config, session_factory, account_id, depth)
    return None


async def _execute_update_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_update_record as _fu
    await _fu(config, session_factory, account_id)
    return None


async def _execute_delete_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_delete_record as _fd
    await _fd(config, session_factory, account_id)
    return None


async def _execute_enqueue_job(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> Any:
    from snackbase.infrastructure.hooks.action_executor import _execute_enqueue_job as _fj
    await _fj(config, session_factory, account_id)
    return None


# ---------------------------------------------------------------------------
# New F8.2-specific action executors
# ---------------------------------------------------------------------------


async def _execute_query_records(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> list[dict[str, Any]]:
    """Query records from a collection and return the result list.

    Config keys:
        collection (str, required): Target collection name.
        filter (str, optional): Filter expression string.
        limit (int, optional): Maximum number of records to return (default 50).
        offset (int, optional): Pagination offset (default 0).
        sort (str, optional): Sort field, optionally prefixed with - for DESC.
    """
    collection = config.get("collection", "")
    if not collection:
        raise ValueError("query_records action requires a 'collection'")

    filter_expr = config.get("filter")
    limit = int(config.get("limit", 50))
    offset = int(config.get("offset", 0))
    sort = config.get("sort")

    try:
        from snackbase.infrastructure.persistence.repositories.records_repository import (
            RecordsRepository,
        )
        async with session_factory() as session:
            repo = RecordsRepository(session)
            records, _total = await repo.list_records(
                collection_name=collection,
                account_id=account_id,
                filter_str=filter_expr,
                sort=sort,
                limit=limit,
                offset=offset,
            )
            return records
    except Exception as exc:
        raise RuntimeError(
            f"query_records failed for collection '{collection}': {exc}"
        ) from exc


async def _execute_aggregate_records(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> dict[str, Any]:
    """Aggregate records in a collection and return the result.

    Config keys:
        collection (str, required): Target collection name.
        function (str, required): Aggregation function: "count", "sum", "avg", "min", "max".
        field (str, optional): Target field for sum/avg/min/max (not needed for count).
        filter (str, optional): Filter expression to restrict rows before aggregating.
        group_by (str, optional): Field name to group results by.
    """
    collection = config.get("collection", "")
    function = config.get("function", "count").lower()
    agg_field = config.get("field")
    group_by = config.get("group_by")

    if not collection:
        raise ValueError("aggregate_records action requires a 'collection'")

    valid_functions = {"count", "sum", "avg", "min", "max"}
    if function not in valid_functions:
        raise ValueError(
            f"aggregate_records: unknown function '{function}'. "
            f"Supported: {', '.join(sorted(valid_functions))}"
        )
    if function != "count" and not agg_field:
        raise ValueError(
            f"aggregate_records: function '{function}' requires a 'field'"
        )

    try:
        from sqlalchemy import text

        async with session_factory() as session:
            # Build a raw SQL query against the dynamic table
            # Using text() to stay DB-agnostic — the collection table must exist
            table_name = collection.lower().replace("-", "_")

            if group_by:
                if function == "count":
                    sql = text(
                        f"SELECT {group_by}, COUNT(*) as value "  # noqa: S608
                        f"FROM {table_name} "
                        f"WHERE account_id = :account_id "
                        f"GROUP BY {group_by}"
                    )
                else:
                    sql = text(
                        f"SELECT {group_by}, {function.upper()}({agg_field}) as value "  # noqa: S608
                        f"FROM {table_name} "
                        f"WHERE account_id = :account_id "
                        f"GROUP BY {group_by}"
                    )
                result = await session.execute(sql, {"account_id": account_id})
                rows = result.mappings().all()
                return {"groups": [dict(row) for row in rows]}
            else:
                if function == "count":
                    sql = text(
                        f"SELECT COUNT(*) as value FROM {table_name} "  # noqa: S608
                        f"WHERE account_id = :account_id"
                    )
                else:
                    sql = text(
                        f"SELECT {function.upper()}({agg_field}) as value "  # noqa: S608
                        f"FROM {table_name} WHERE account_id = :account_id"
                    )
                result = await session.execute(sql, {"account_id": account_id})
                row = result.mappings().first()
                return {"value": row["value"] if row else None}

    except Exception as exc:
        raise RuntimeError(
            f"aggregate_records failed for collection '{collection}': {exc}"
        ) from exc


async def _execute_transform(
    config: dict[str, Any],
    ctx: EndpointRequestContext,
) -> Any:
    """Transform/reshape data using template expressions.

    Config keys:
        output (dict | list | str, required): Output template with {{...}} variables.
            Can reference any context variables including action results.

    Returns the resolved output value (dict, list, or string).
    """
    output = config.get("output")
    if output is None:
        raise ValueError("transform action requires an 'output' key")

    return _resolve_value(output, ctx)


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------


async def _run_actions(
    actions: list[dict[str, Any]],
    ctx: EndpointRequestContext,
    session_factory: Any,
    depth: int,
) -> tuple[list[Any], int, str | None]:
    """Internal: execute actions sequentially, populating ctx.action_results.

    Returns:
        Tuple of (action_results, actions_executed, error_message).
    """
    if depth >= _MAX_DEPTH:
        return [], 0, (
            f"Maximum execution depth ({_MAX_DEPTH}) exceeded — possible cycle detected"
        )

    account_id = ctx.auth_account_id or None
    executed = 0

    for action in actions:
        action_type = action.get("type", "")
        resolved = _resolve_action(action, ctx)

        try:
            result: Any = None

            if action_type == "send_webhook":
                result = await _execute_send_webhook(resolved)

            elif action_type == "send_email":
                result = await _execute_send_email(resolved, session_factory)

            elif action_type == "create_record":
                result = await _execute_create_record(resolved, session_factory, account_id, depth)

            elif action_type == "update_record":
                result = await _execute_update_record(resolved, session_factory, account_id)

            elif action_type == "delete_record":
                result = await _execute_delete_record(resolved, session_factory, account_id)

            elif action_type == "enqueue_job":
                result = await _execute_enqueue_job(resolved, session_factory, account_id)

            elif action_type == "query_records":
                result = await _execute_query_records(resolved, session_factory, account_id)

            elif action_type == "aggregate_records":
                result = await _execute_aggregate_records(resolved, session_factory, account_id)

            elif action_type == "transform":
                # transform reads from the live ctx (action_results already populated)
                result = await _execute_transform(resolved, ctx)

            else:
                logger.warning("Unknown action type — skipping", action_type=action_type)
                ctx.action_results.append(None)
                continue

            ctx.action_results.append(result)
            executed += 1

        except Exception as exc:
            error = f"Action '{action_type}' failed: {exc}"
            logger.error("Endpoint action failed", action_type=action_type, error=str(exc))
            ctx.action_results.append(None)
            return ctx.action_results, executed, error

    return ctx.action_results, executed, None


async def execute_endpoint_actions(
    actions: list[dict[str, Any]],
    ctx: EndpointRequestContext,
    session_factory: Any,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    depth: int = 0,
) -> tuple[list[Any], int, str | None]:
    """Execute a list of endpoint actions with a configurable timeout.

    Actions run sequentially. Each action's result is appended to
    ``ctx.action_results`` so subsequent actions and the response template
    can reference it via ``{{actions[N].result}}``.

    Args:
        actions: List of action dicts from the endpoint's ``actions`` field.
        ctx: Request context (body, query, params, auth, action_results).
        session_factory: Async session factory for DB-accessing actions.
        timeout: Execution timeout in seconds (default 30).
        depth: Current execution depth (cycle prevention).

    Returns:
        Tuple of (action_results, actions_executed, error_message).
        error_message is None on full success.
    """
    try:
        return await asyncio.wait_for(
            _run_actions(actions, ctx, session_factory, depth),
            timeout=timeout,
        )
    except TimeoutError:
        return ctx.action_results, len(ctx.action_results), (
            f"Endpoint execution timed out after {timeout:.0f}s"
        )
