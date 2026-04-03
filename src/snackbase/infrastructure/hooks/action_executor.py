"""Action executor for F8.1 API-defined hooks.

Resolves template variables in action configs, then dispatches each action
type. Supports: send_webhook, send_email, create_record, update_record,
delete_record, enqueue_job.

Template variables resolved in string values:
    {{record.field}}   — field from the triggering record
    {{auth.user_id}}   — authenticated user ID from hook context
    {{auth.email}}     — authenticated user email from hook context
    {{now}}            — current UTC ISO timestamp
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from snackbase.core.logging import get_logger
from snackbase.domain.entities.hook_context import HookContext

logger = get_logger(__name__)

# Maximum hook execution depth to prevent infinite loops
_MAX_DEPTH = 5

# Template variable pattern: {{variable.path}}
_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")


def _resolve_template(value: str, record: dict[str, Any], context: HookContext | None) -> str:
    """Replace {{...}} placeholders in a string value.

    Supported variables:
        record.<field>   — data from the triggering record
        auth.user_id     — user ID from hook context
        auth.email       — user email from hook context
        now              — current UTC ISO timestamp
    """
    now_str = datetime.now(UTC).isoformat()

    def _replace(match: re.Match) -> str:
        var = match.group(1).strip()

        if var == "now":
            return now_str

        if var.startswith("record."):
            field = var[len("record."):]
            val = record.get(field)
            return str(val) if val is not None else ""

        if var == "auth.user_id":
            if context and context.user:
                return context.user.id or ""
            return ""

        if var == "auth.email":
            if context and context.user:
                return getattr(context.user, "email", "") or ""
            return ""

        # Unknown variable — leave as-is so config errors are visible
        return match.group(0)

    return _TEMPLATE_RE.sub(_replace, value)


def _resolve_value(value: Any, record: dict[str, Any], context: HookContext | None) -> Any:
    """Recursively resolve template variables in dicts, lists, and strings."""
    if isinstance(value, str):
        return _resolve_template(value, record, context)
    if isinstance(value, dict):
        return {k: _resolve_value(v, record, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, record, context) for item in value]
    return value


def _resolve_action(action: dict[str, Any], record: dict[str, Any], context: HookContext | None) -> dict[str, Any]:
    """Return a copy of the action with all template variables resolved."""
    return {k: _resolve_value(v, record, context) for k, v in action.items()}


async def _execute_send_webhook(config: dict[str, Any]) -> None:
    """Fire an outbound HTTP request."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx is required for send_webhook actions")

    url = config.get("url", "")
    if not url:
        raise ValueError("send_webhook action requires a 'url'")

    method = config.get("method", "POST").upper()
    headers = config.get("headers") or {}
    body_template = config.get("body_template")

    request_kwargs: dict[str, Any] = {"headers": headers}
    if body_template is not None:
        request_kwargs["content"] = body_template
        if "content-type" not in {k.lower() for k in headers}:
            request_kwargs["headers"] = {**headers, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, **request_kwargs)
        response.raise_for_status()
        logger.debug("send_webhook delivered", url=url, status=response.status_code)


async def _execute_send_email(config: dict[str, Any], session_factory: Any) -> None:
    """Send an email via the SnackBase email service."""
    to_addr = config.get("to", "")
    if not to_addr:
        raise ValueError("send_email action requires a 'to' address")

    subject = config.get("subject", "Hook notification")
    body = config.get("body", "")
    template_id = config.get("template_id")
    variables = config.get("variables") or {}

    try:
        from snackbase.infrastructure.services.email_service import get_email_service
        email_service = await get_email_service(session_factory)
        if template_id:
            await email_service.send_template(
                to=to_addr,
                template_id=template_id,
                variables=variables,
            )
        else:
            await email_service.send(
                to=to_addr,
                subject=subject,
                body=body,
            )
    except Exception as exc:
        raise RuntimeError(f"send_email failed: {exc}") from exc


async def _execute_create_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
    depth: int,
) -> None:
    """Create a record in a collection."""
    collection = config.get("collection", "")
    data = config.get("data") or {}
    if not collection:
        raise ValueError("create_record action requires a 'collection'")

    # Pass depth through payload so recursive hooks can detect cycles
    ctx_data = {"_depth": depth + 1}

    try:
        from snackbase.infrastructure.persistence.repositories.records_repository import (
            RecordsRepository,
        )
        async with session_factory() as session:
            repo = RecordsRepository(session)
            record_data = {**data, "account_id": account_id, **ctx_data}
            await repo.create_record(collection, record_data)
            await session.commit()
    except Exception as exc:
        raise RuntimeError(f"create_record failed for collection '{collection}': {exc}") from exc


async def _execute_update_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> None:
    """Update an existing record in a collection."""
    collection = config.get("collection", "")
    record_id = config.get("record_id", "")
    data = config.get("data") or {}
    if not collection or not record_id:
        raise ValueError("update_record action requires 'collection' and 'record_id'")

    try:
        from snackbase.infrastructure.persistence.repositories.records_repository import (
            RecordsRepository,
        )
        async with session_factory() as session:
            repo = RecordsRepository(session)
            await repo.update_record(collection, record_id, data, account_id=account_id)
            await session.commit()
    except Exception as exc:
        raise RuntimeError(
            f"update_record failed for collection '{collection}' record '{record_id}': {exc}"
        ) from exc


async def _execute_delete_record(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> None:
    """Delete a record from a collection."""
    collection = config.get("collection", "")
    record_id = config.get("record_id", "")
    if not collection or not record_id:
        raise ValueError("delete_record action requires 'collection' and 'record_id'")

    try:
        from snackbase.infrastructure.persistence.repositories.records_repository import (
            RecordsRepository,
        )
        async with session_factory() as session:
            repo = RecordsRepository(session)
            await repo.delete_record(collection, record_id, account_id=account_id)
            await session.commit()
    except Exception as exc:
        raise RuntimeError(
            f"delete_record failed for collection '{collection}' record '{record_id}': {exc}"
        ) from exc


async def _execute_enqueue_job(
    config: dict[str, Any],
    session_factory: Any,
    account_id: str | None,
) -> None:
    """Enqueue a background job."""
    handler = config.get("handler", "")
    if not handler:
        raise ValueError("enqueue_job action requires a 'handler'")

    payload = config.get("payload") or {}

    from snackbase.infrastructure.persistence.models.job import JobModel
    from snackbase.infrastructure.persistence.repositories.job_repository import JobRepository

    async with session_factory() as session:
        job_repo = JobRepository(session)
        job = JobModel(
            handler=handler,
            payload=payload,
            queue="default",
            account_id=account_id,
        )
        await job_repo.create(job)
        await session.commit()
        logger.debug("enqueue_job dispatched", handler=handler, job_id=job.id)


async def execute_actions(
    actions: list[dict[str, Any]],
    record: dict[str, Any],
    context: HookContext | None,
    session_factory: Any,
    depth: int = 0,
) -> tuple[int, str | None]:
    """Execute a list of hook actions, returning (count_executed, error_message).

    Actions are executed sequentially. On failure, remaining actions are skipped
    and the error is returned.

    Args:
        actions: List of action dicts from the hook's ``actions`` field.
        record: The record data that triggered the hook.
        context: Hook context (user, account_id, etc.).
        session_factory: Async session factory for DB-accessing actions.
        depth: Current execution depth (prevents infinite recursion).

    Returns:
        Tuple of (number of actions executed, error message or None).
    """
    if depth >= _MAX_DEPTH:
        return 0, f"Maximum hook execution depth ({_MAX_DEPTH}) exceeded — possible cycle detected"

    account_id = context.account_id if context else None
    executed = 0

    for action in actions:
        action_type = action.get("type", "")
        resolved = _resolve_action(action, record, context)

        try:
            if action_type == "send_webhook":
                await _execute_send_webhook(resolved)

            elif action_type == "send_email":
                await _execute_send_email(resolved, session_factory)

            elif action_type == "create_record":
                await _execute_create_record(resolved, session_factory, account_id, depth)

            elif action_type == "update_record":
                await _execute_update_record(resolved, session_factory, account_id)

            elif action_type == "delete_record":
                await _execute_delete_record(resolved, session_factory, account_id)

            elif action_type == "enqueue_job":
                await _execute_enqueue_job(resolved, session_factory, account_id)

            else:
                logger.warning("Unknown action type — skipping", action_type=action_type)
                continue

            executed += 1

        except Exception as exc:
            error = f"Action '{action_type}' failed: {exc}"
            logger.error("Hook action failed", action_type=action_type, error=str(exc))
            return executed, error

    return executed, None
