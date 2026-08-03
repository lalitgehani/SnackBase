"""Public invoke dispatcher for Functions at /api/v1/f/{account_slug}/{slug}."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import Settings, get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.functions.concurrency import get_function_concurrency_limiter
from snackbase.infrastructure.functions.nested_budget import get_nested_invoke_budget
from snackbase.infrastructure.functions.redaction import redact_request_data, truncate_text
from snackbase.infrastructure.functions.runner import FunctionRunner, InvokeResult
from snackbase.infrastructure.persistence.database import get_db_manager
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.function import (
    FunctionExecutionModel,
    FunctionModel,
    FunctionVersionModel,
)
from snackbase.infrastructure.persistence.repositories.function_repository import (
    FunctionRepository,
)
from snackbase.infrastructure.security.encryption import EncryptionService

logger = get_logger(__name__)

router = APIRouter(tags=["Function Invoke"])


async def _resolve_account(session: AsyncSession, account_slug: str) -> AccountModel | None:
    result = await session.execute(
        select(AccountModel).where(AccountModel.slug == account_slug)
    )
    return result.scalar_one_or_none()


def _cors_headers(request: Request, settings: Settings) -> dict[str, str]:
    origins = settings.function_cors_origins or ["*"]
    origin = request.headers.get("origin")
    headers: dict[str, str] = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD",
        "Access-Control-Allow-Headers": request.headers.get(
            "access-control-request-headers",
            "authorization, content-type, x-function-depth, x-function-root",
        ),
        "Access-Control-Max-Age": "86400",
        "Access-Control-Expose-Headers": "X-Function-Execution-Id",
    }
    if "*" in origins:
        headers["Access-Control-Allow-Origin"] = origin or "*"
    elif origin and origin in origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    # If origin not allowed, omit ACAO
    return headers


def _extract_auth(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "authenticated_user", None)
    if not user:
        return {}
    return {
        "user_id": getattr(user, "user_id", None),
        "email": getattr(user, "email", None),
        "account_id": getattr(user, "account_id", None),
        "role": getattr(user, "role", None),
    }


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    parts = auth.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


async def build_invoke_env(
    *,
    request: Request,
    fn: FunctionModel,
    account_id: str,
    auth: dict[str, Any],
    repo: FunctionRepository,
    caller_token: str | None,
    account_slug: str | None = None,
) -> dict[str, str]:
    """Build allowlisted env for the child process."""
    settings = get_settings()
    base_url = str(request.base_url).rstrip("/")
    # Prefer configured public URL if available
    snackbase_url = getattr(settings, "public_url", None) or base_url

    grants = fn.grants or {}
    caps = grants.get("capabilities") if isinstance(grants, dict) else grants
    if isinstance(caps, list):
        grants_csv = ",".join(str(c) for c in caps)
    else:
        grants_csv = ""

    env: dict[str, str] = {
        "SNACKBASE_URL": snackbase_url,
        "FN_SLUG": fn.slug,
        "FN_ACCOUNT_ID": account_id,
        "FN_FUNCTION_ID": fn.id,
        "SNACKBASE_FUNCTION_GRANTS": grants_csv,
    }
    if account_slug:
        env["FN_ACCOUNT_SLUG"] = account_slug
    if caller_token:
        env["SNACKBASE_CALLER_TOKEN"] = caller_token

    # Admin token: mint a short-lived service token if JWT service available
    admin_token = await _mint_admin_token(account_id=account_id, user=auth)
    if admin_token:
        env["SNACKBASE_ADMIN_TOKEN"] = admin_token

    # Inject decrypted function secrets
    secrets = await repo.get_all_secrets_for_inject(account_id)
    if secrets:
        enc = EncryptionService(settings.encryption_key)
        for secret in secrets:
            try:
                env[secret.name] = enc.decrypt(secret.value_encrypted)
            except Exception:
                logger.warning(
                    "Failed to decrypt function secret",
                    name=secret.name,
                    account_id=account_id,
                )
    return env


async def _mint_admin_token(*, account_id: str, user: dict[str, Any]) -> str | None:
    """Create a short-lived admin-scoped JWT for get_admin_client()."""
    try:
        from snackbase.infrastructure.auth.jwt_service import jwt_service

        return jwt_service.create_access_token(
            user_id=user.get("user_id") or "function-runtime",
            account_id=account_id,
            email=user.get("email") or "function@runtime.local",
            role="admin",
        )
    except Exception:
        logger.debug("Could not mint admin token for function", exc_info=True)
        return None


async def run_and_log_execution(
    *,
    repo: FunctionRepository,
    session: AsyncSession,
    fn: FunctionModel,
    version: FunctionVersionModel,
    request_payload: dict[str, Any],
    extra_env: dict[str, str],
    settings: Settings,
) -> InvokeResult:
    runner = FunctionRunner(
        timeout_seconds=settings.function_execution_timeout_seconds,
        streaming_timeout_seconds=settings.function_streaming_timeout_seconds,
        stdout_max_bytes=settings.function_stdout_max_bytes,
    )
    execution_id = str(uuid.uuid4())
    extra_env = {**extra_env, "FN_EXECUTION_ID": execution_id}

    from snackbase.infrastructure.functions.worker_pool import get_function_worker_pool

    pool = get_function_worker_pool()
    # Offload to worker pool — never call submit_sync/future.result on the event loop
    result = await pool.submit(
        runner,
        env_path=version.env_path or "",
        source_files=dict(version.source_files or {}),
        entrypoint=fn.entrypoint or "handler.py",
        request_payload=request_payload,
        extra_env=extra_env,
        execution_id=execution_id,
    )
    if result.http_status == 429 and result.status == "failed":
        return result

    redacted_req = redact_request_data(
        method=str(request_payload.get("method") or "POST"),
        path=str(request_payload.get("path") or "/"),
        headers=request_payload.get("headers"),
        query=request_payload.get("query"),
        body=request_payload.get("json")
        if request_payload.get("json") is not None
        else request_payload.get("body"),
    )
    # Never persist secret values; streaming stores truncated summary only
    body_out = result.body
    if result.streaming:
        summary = "".join(result.stream_chunks) if result.stream_chunks else (body_out or "")
        body_out = {
            "streaming": True,
            "summary": truncate_text(str(summary), 2048),
            "chunk_count": len(result.stream_chunks),
        }
    elif isinstance(body_out, str):
        body_out = truncate_text(body_out, 8192)

    execution = FunctionExecutionModel(
        id=result.execution_id,
        function_id=fn.id,
        version_id=version.id,
        status=result.status,
        http_status=result.http_status,
        duration_ms=result.duration_ms,
        request_data=redacted_req,
        response_body=body_out,
        stdout=result.stdout,
        stderr=result.stderr,
        error_message=result.error_message,
        used_admin_client=result.used_admin_client,
    )
    await repo.create_execution(execution)
    await session.commit()
    return result


async def _handle_invoke(
    request: Request,
    account_slug: str,
    slug: str,
    path_suffix: str = "",
) -> Response:
    settings = get_settings()
    cors = _cors_headers(request, settings)

    if request.method == "OPTIONS":
        return Response(status_code=204, headers=cors)

    # Body size check
    body = await request.body()
    if len(body) > settings.max_function_request_body_bytes:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
            headers=cors,
        )

    # Nested depth
    try:
        depth = int(request.headers.get("x-function-depth") or "0")
    except ValueError:
        depth = 0
    root_key = request.headers.get("x-function-root") or f"{account_slug}:{slug}"
    budget = get_nested_invoke_budget()
    if not budget.check_and_increment(root_key, depth):
        return JSONResponse(
            status_code=429,
            content={"detail": "Nested function invoke budget exceeded"},
            headers=cors,
        )

    db_manager = get_db_manager()
    async with db_manager.session() as session:
        account = await _resolve_account(session, account_slug)
        if not account:
            return JSONResponse(
                status_code=404,
                content={"detail": "Account not found"},
                headers=cors,
            )

        repo = FunctionRepository(session)
        fn = await repo.get_by_slug(account.id, slug)
        if not fn or not fn.enabled or fn.status == "REMOVED":
            return JSONResponse(
                status_code=404,
                content={"detail": "Function not found"},
                headers=cors,
            )
        if fn.status == "THROTTLED":
            return JSONResponse(
                status_code=429,
                content={"detail": "Function is throttled"},
                headers=cors,
            )

        auth = _extract_auth(request)
        if fn.auth_required:
            if not auth.get("user_id"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"},
                    headers={**cors, "WWW-Authenticate": "Bearer"},
                )
            if auth.get("account_id") != account.id:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Token account does not match function account"},
                    headers=cors,
                )

        if not fn.active_version_id:
            return JSONResponse(
                status_code=404,
                content={"detail": "Function has no deployed version"},
                headers=cors,
            )
        version = await repo.get_version(fn.active_version_id)
        if not version or not version.env_path:
            return JSONResponse(
                status_code=500,
                content={"detail": "Function environment unavailable"},
                headers=cors,
            )

        limiter = get_function_concurrency_limiter()
        if not limiter.try_acquire(account.id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many concurrent function invokes"},
                headers=cors,
            )

        try:
            # Parse JSON body if applicable
            parsed_body: Any = None
            content_type = (request.headers.get("content-type") or "").lower()
            if body and "application/json" in content_type:
                try:
                    parsed_body = json.loads(body)
                except json.JSONDecodeError:
                    parsed_body = None

            path = "/" + path_suffix if path_suffix else "/"
            request_payload = {
                "method": request.method.upper(),
                "path": path,
                "headers": {k: v for k, v in request.headers.items()},
                "query": dict(request.query_params),
                "json": parsed_body,
                "body": parsed_body if parsed_body is not None else body.decode("utf-8", "replace"),
                "body_bytes": body.decode("latin-1") if body else "",
                "auth": auth,
            }
            extra_env = await build_invoke_env(
                request=request,
                fn=fn,
                account_id=account.id,
                auth=auth,
                repo=repo,
                caller_token=_extract_bearer(request),
                account_slug=account_slug,
            )
            # Propagate nested depth for outbound self-invokes
            extra_env["FN_DEPTH"] = str(depth)
            extra_env["FN_ROOT"] = root_key

            result = await run_and_log_execution(
                repo=repo,
                session=session,
                fn=fn,
                version=version,
                request_payload=request_payload,
                extra_env=extra_env,
                settings=settings,
            )
        finally:
            limiter.release(account.id)

        resp_headers = {**cors, **result.headers, "X-Function-Execution-Id": result.execution_id}
        # Remove hop-by-hop
        resp_headers.pop("content-length", None)
        resp_headers.pop("transfer-encoding", None)

        if result.status == "timeout":
            return JSONResponse(
                status_code=504,
                content={"detail": result.error_message or "Function timed out"},
                headers=resp_headers,
            )

        media = (
            result.media_type
            or result.headers.get("content-type")
            or result.headers.get("Content-Type")
        )

        # True chunked/SSE response when handler returned a stream
        if result.streaming and result.stream_chunks is not None:
            media_type = media or "text/event-stream"

            def _chunk_iter() -> Any:
                for chunk in result.stream_chunks:
                    if isinstance(chunk, bytes):
                        yield chunk
                    else:
                        yield str(chunk).encode("utf-8")

            return StreamingResponse(
                _chunk_iter(),
                status_code=result.http_status,
                headers=resp_headers,
                media_type=media_type,
            )

        if media and "application/json" in media:
            return JSONResponse(
                status_code=result.http_status,
                content=result.body,
                headers=resp_headers,
            )
        if isinstance(result.body, (dict, list)):
            return JSONResponse(
                status_code=result.http_status,
                content=result.body,
                headers=resp_headers,
            )
        content: bytes | str
        if result.body is None:
            content = b""
        elif isinstance(result.body, bytes):
            content = result.body
        else:
            content = str(result.body)
        return Response(
            content=content,
            status_code=result.http_status,
            headers=resp_headers,
            media_type=media,
        )


async def invoke_function(
    request: Request,
    account_slug: str,
    slug: str,
) -> Response:
    return await _handle_invoke(request, account_slug, slug, "")


async def invoke_function_with_path(
    request: Request,
    account_slug: str,
    slug: str,
    path: str,
) -> Response:
    return await _handle_invoke(request, account_slug, slug, path)


# Register one operation_id per method to avoid OpenAPI duplicate-ID warnings
for _method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"):
    router.add_api_route(
        "/{account_slug}/{slug}",
        invoke_function,
        methods=[_method],
        operation_id=f"invoke_function_{_method.lower()}",
        response_model=None,
    )
    router.add_api_route(
        "/{account_slug}/{slug}/{path:path}",
        invoke_function_with_path,
        methods=[_method],
        operation_id=f"invoke_function_path_{_method.lower()}",
        response_model=None,
    )
