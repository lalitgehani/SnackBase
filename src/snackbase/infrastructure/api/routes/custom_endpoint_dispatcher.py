"""Dispatcher for custom endpoint invocations (F8.2).

Registers a single catch-all route at /api/v1/x/{account_slug}/{path:path}
that dispatches incoming HTTP requests to the matching custom endpoint
definition stored in the database.

Request flow:
1. Resolve account_slug → account_id (404 if not found)
2. Collect all enabled endpoints for the account
3. Convert stored path templates (e.g. /users/:id/orders) to regexes and
   find the first that matches the incoming path + method (404 if none)
4. If auth_required=True, require a valid auth token (401 if missing)
5. Evaluate optional condition expression (403 if fails)
6. Build EndpointRequestContext from request body, query params, path params
7. Execute action pipeline via execute_endpoint_actions (30s timeout)
8. Render response_template with resolved action results
9. Log execution to endpoint_executions table
10. Return the configured HTTP response
"""

from __future__ import annotations

import re
import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from snackbase.core.logging import get_logger
from snackbase.infrastructure.endpoints.endpoint_executor import (
    EndpointRequestContext,
    execute_endpoint_actions,
)
from snackbase.infrastructure.persistence.models.endpoint import EndpointModel

logger = get_logger(__name__)

router = APIRouter(tags=["Custom Endpoints"])

# Supported HTTP methods for custom endpoints
_SUPPORTED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


# ---------------------------------------------------------------------------
# Path template → regex conversion
# ---------------------------------------------------------------------------


def _path_template_to_regex(template: str) -> re.Pattern:  # type: ignore[type-arg]
    """Convert a path template with :param segments to a named-group regex.

    Example:
        /users/:user_id/orders  →  ^/users/(?P<user_id>[^/]+)/orders$
    """
    # Escape dots, then replace :param with named groups
    escaped = re.sub(r"[.]", r"\\.", template)
    pattern = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"(?P<\1>[^/]+)", escaped)
    return re.compile(f"^{pattern}$")


def _match_endpoint(
    endpoint: EndpointModel,
    method: str,
    incoming_path: str,
) -> dict[str, str] | None:
    """Try to match an endpoint against the incoming method and path.

    Args:
        endpoint: The EndpointModel to test.
        method: Incoming HTTP method (uppercased).
        incoming_path: Incoming path starting with /.

    Returns:
        Dict of extracted path parameters if matched, or None if no match.
    """
    if endpoint.method != method:
        return None

    pattern = _path_template_to_regex(endpoint.path)
    m = pattern.match(incoming_path)
    if m is None:
        return None

    return m.groupdict()


# ---------------------------------------------------------------------------
# Response template rendering
# ---------------------------------------------------------------------------


def _render_response_template(
    template: dict[str, Any] | None,
    ctx: EndpointRequestContext,
) -> tuple[int, Any, dict[str, str]]:
    """Render the response template into (status_code, body, headers).

    If no template is set, returns the last action result (or {}) with 200.

    Template format:
        {
            "status": 200,
            "body": { "key": "{{actions[0].result}}" },
            "headers": { "X-Custom": "value" }
        }
    """
    from snackbase.infrastructure.endpoints.endpoint_executor import _resolve_value

    if not template:
        last_result = ctx.action_results[-1] if ctx.action_results else {}
        body = last_result if last_result is not None else {}
        return 200, body, {}

    status_code = int(template.get("status", 200))
    raw_body = template.get("body", {})
    raw_headers = template.get("headers", {})

    resolved_body = _resolve_value(raw_body, ctx)
    resolved_headers: dict[str, str] = {}
    if isinstance(raw_headers, dict):
        for k, v in raw_headers.items():
            resolved_headers[str(k)] = str(_resolve_value(v, ctx))

    return status_code, resolved_body, resolved_headers


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


def _evaluate_condition(condition: str, ctx: EndpointRequestContext) -> bool:
    """Evaluate a rule expression condition against the request context.

    Returns True if the condition passes (or evaluation fails — safe default).
    """
    try:
        from snackbase.core.rules.evaluator import evaluate_expression

        rule_context = {
            "auth": {
                "user_id": ctx.auth_user_id,
                "email": ctx.auth_email,
                "account_id": ctx.auth_account_id,
            },
            "request": {
                "body": ctx.request_body,
                "query": ctx.request_query,
                "params": ctx.request_params,
            },
        }
        result = evaluate_expression(condition, rule_context)
        return bool(result)
    except Exception as exc:
        logger.warning(
            "Endpoint condition evaluation failed — denying request",
            condition=condition,
            error=str(exc),
        )
        return False


# ---------------------------------------------------------------------------
# Execution logging
# ---------------------------------------------------------------------------


async def _log_execution(
    endpoint_id: str,
    status: str,
    http_status: int,
    duration_ms: int | None,
    request_data: dict[str, Any] | None,
    response_body: Any,
    error_message: str | None,
    session_factory: Any,
) -> None:
    """Persist an execution record to the endpoint_executions table."""
    try:
        from snackbase.infrastructure.persistence.models.endpoint_execution import (
            EndpointExecutionModel,
        )
        from snackbase.infrastructure.persistence.repositories.endpoint_execution_repository import (
            EndpointExecutionRepository,
        )

        async with session_factory() as session:
            repo = EndpointExecutionRepository(session)
            execution = EndpointExecutionModel(
                endpoint_id=endpoint_id,
                status=status,
                http_status=http_status,
                duration_ms=duration_ms,
                request_data=request_data,
                response_body=response_body if isinstance(response_body, (dict, list)) else None,
                error_message=error_message,
            )
            await repo.create(execution)
            await session.commit()
    except Exception as exc:
        logger.warning(
            "Failed to log endpoint execution",
            endpoint_id=endpoint_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Main dispatcher handler
# ---------------------------------------------------------------------------


async def _handle_custom_endpoint(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Core dispatcher logic shared by all method handlers."""
    from snackbase.infrastructure.persistence.database import get_db_manager
    from snackbase.infrastructure.persistence.repositories.account_repository import (
        AccountRepository,
    )
    from snackbase.infrastructure.persistence.repositories.endpoint_repository import (
        EndpointRepository,
    )

    db_manager = get_db_manager()
    method = request.method.upper()
    incoming_path = f"/{path}" if not path.startswith("/") else path

    async with db_manager.session() as session:
        # 1. Resolve account slug → account_id
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_slug(account_slug)
        if account is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Account '{account_slug}' not found"},
            )

        account_id = account.id

        # 2. Find matching enabled endpoint
        endpoint_repo = EndpointRepository(session)
        enabled_endpoints = await endpoint_repo.get_all_enabled_for_account(account_id)

        matched_endpoint: EndpointModel | None = None
        path_params: dict[str, str] = {}

        for ep in enabled_endpoints:
            params = _match_endpoint(ep, method, incoming_path)
            if params is not None:
                matched_endpoint = ep
                path_params = params
                break

        if matched_endpoint is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "No matching custom endpoint found"},
            )

    # 3. Auth check (outside the first session scope; uses request state)
    if matched_endpoint.auth_required:
        if not hasattr(request.state, "authenticated_user"):
            auth_error = getattr(
                request.state, "auth_error", "Authentication required"
            )
            return JSONResponse(
                status_code=401,
                content={"detail": auth_error},
                headers={"WWW-Authenticate": "Bearer"},
            )
        auth_user = request.state.authenticated_user
        # Verify the authenticated user belongs to this account
        if auth_user.account_id != account_id:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: account mismatch"},
            )
    else:
        auth_user = getattr(request.state, "authenticated_user", None)

    # 4. Build request context
    try:
        request_body: dict[str, Any] = {}
        content_type = request.headers.get("content-type", "")
        if method in ("POST", "PUT", "PATCH") and "application/json" in content_type:
            try:
                request_body = await request.json()
            except Exception:
                request_body = {}
    except Exception:
        request_body = {}

    request_query: dict[str, str] = {k: v for k, v in request.query_params.items()}

    ctx = EndpointRequestContext(
        request_body=request_body,
        request_query=request_query,
        request_params=path_params,
        auth_user_id=auth_user.user_id if auth_user else "",
        auth_email=getattr(auth_user, "email", "") if auth_user else "",
        auth_account_id=account_id,
    )

    # 5. Evaluate condition
    if matched_endpoint.condition:
        if not _evaluate_condition(matched_endpoint.condition, ctx):
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: condition not satisfied"},
            )

    # 6. Execute action pipeline
    start_ms = int(time.monotonic() * 1000)

    try:
        from snackbase.core.config import get_settings
        settings = get_settings()
        timeout = getattr(settings, "endpoint_execution_timeout_seconds", 30)
    except Exception:
        timeout = 30

    action_results, actions_executed, error_message = await execute_endpoint_actions(
        actions=matched_endpoint.actions or [],
        ctx=ctx,
        session_factory=db_manager.session,
        timeout=float(timeout),
    )

    duration_ms = int(time.monotonic() * 1000) - start_ms

    # 7. Render response
    exec_status: str
    if error_message:
        exec_status = "partial" if actions_executed > 0 else "failed"
        # Still try to render the template even on partial failure
        try:
            http_status, body, headers = _render_response_template(
                matched_endpoint.response_template, ctx
            )
        except Exception:
            http_status = 500
            body = {"detail": error_message}
            headers = {}
    else:
        exec_status = "success"
        http_status, body, headers = _render_response_template(
            matched_endpoint.response_template, ctx
        )

    # 8. Log execution (fire-and-forget — never fails the request)
    request_snapshot = {
        "method": method,
        "path": incoming_path,
        "body": request_body,
        "query": request_query,
        "params": path_params,
    }
    await _log_execution(
        endpoint_id=matched_endpoint.id,
        status=exec_status,
        http_status=http_status,
        duration_ms=duration_ms,
        request_data=request_snapshot,
        response_body=body,
        error_message=error_message,
        session_factory=db_manager.session,
    )

    logger.info(
        "Custom endpoint dispatched",
        endpoint_id=matched_endpoint.id,
        method=method,
        path=incoming_path,
        http_status=http_status,
        duration_ms=duration_ms,
        status=exec_status,
    )

    return JSONResponse(
        status_code=http_status,
        content=body,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Route registrations — one per HTTP method
# ---------------------------------------------------------------------------
# FastAPI does not support a single route handler bound to multiple methods,
# so we register one per supported method.


@router.get("/{account_slug}/{path:path}")
async def dispatch_get(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Dispatch a GET request to a custom endpoint."""
    return await _handle_custom_endpoint(request, account_slug, path)


@router.post("/{account_slug}/{path:path}")
async def dispatch_post(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Dispatch a POST request to a custom endpoint."""
    return await _handle_custom_endpoint(request, account_slug, path)


@router.put("/{account_slug}/{path:path}")
async def dispatch_put(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Dispatch a PUT request to a custom endpoint."""
    return await _handle_custom_endpoint(request, account_slug, path)


@router.patch("/{account_slug}/{path:path}")
async def dispatch_patch(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Dispatch a PATCH request to a custom endpoint."""
    return await _handle_custom_endpoint(request, account_slug, path)


@router.delete("/{account_slug}/{path:path}")
async def dispatch_delete(request: Request, account_slug: str, path: str) -> JSONResponse:
    """Dispatch a DELETE request to a custom endpoint."""
    return await _handle_custom_endpoint(request, account_slug, path)
