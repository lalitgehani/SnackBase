"""Shared `invoke_function` action for Hooks, Workflows, and Endpoints."""

from __future__ import annotations

from typing import Any

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.functions.redaction import redact_request_data, truncate_text
from snackbase.infrastructure.functions.runner import FunctionRunner, InvokeResult
from snackbase.infrastructure.persistence.models.function import FunctionExecutionModel
from snackbase.infrastructure.persistence.repositories.function_repository import (
    FunctionRepository,
)

logger = get_logger(__name__)


async def execute_invoke_function(
    action: dict[str, Any],
    *,
    session_factory: Any,
    account_id: str | None,
) -> dict[str, Any]:
    """Invoke a tenant function by slug and return a serializable result dict.

    Action config:
        slug: function slug (required)
        payload / body: JSON body
        method: HTTP method (default POST)
        headers: optional headers
        path: optional path suffix (default /)
    """
    if not account_id:
        raise ValueError("account_id is required to invoke a function")

    slug = action.get("slug")
    if not slug:
        raise ValueError("invoke_function requires 'slug'")

    method = str(action.get("method") or "POST").upper()
    path = str(action.get("path") or "/")
    headers = dict(action.get("headers") or {})
    body = action.get("payload") if "payload" in action else action.get("body")

    settings = get_settings()
    async with session_factory() as session:
        repo = FunctionRepository(session)
        fn = await repo.get_by_slug(account_id, slug)
        if not fn or not fn.enabled or fn.status != "ACTIVE":
            raise ValueError(f"Function '{slug}' not found or not invocable")
        if not fn.active_version_id:
            raise ValueError(f"Function '{slug}' has no active version")
        version = await repo.get_version(fn.active_version_id)
        if not version or not version.env_path:
            raise ValueError(f"Function '{slug}' environment unavailable")

        request_payload = {
            "method": method,
            "path": path,
            "headers": headers,
            "query": {},
            "json": body,
            "body": body,
            "auth": {
                "user_id": "automation",
                "email": "automation@snackbase.local",
                "account_id": account_id,
                "role": "admin",
            },
        }

        # Mint admin token for automation context
        extra_env: dict[str, str] = {
            "SNACKBASE_URL": getattr(settings, "public_url", None) or "http://127.0.0.1:8090",
            "FN_SLUG": fn.slug,
            "FN_ACCOUNT_ID": account_id,
            "FN_FUNCTION_ID": fn.id,
        }
        grants = fn.grants or {}
        caps = grants.get("capabilities") if isinstance(grants, dict) else []
        if isinstance(caps, list):
            extra_env["SNACKBASE_FUNCTION_GRANTS"] = ",".join(str(c) for c in caps)
        try:
            from snackbase.infrastructure.auth.jwt_service import jwt_service

            token = jwt_service.create_access_token(
                user_id="automation",
                account_id=account_id,
                email="automation@snackbase.local",
                role="admin",
            )
            extra_env["SNACKBASE_ADMIN_TOKEN"] = token
            extra_env["SNACKBASE_CALLER_TOKEN"] = token
        except Exception:
            logger.debug("Could not mint automation token", exc_info=True)

        # Inject secrets
        try:
            from snackbase.infrastructure.security.encryption import EncryptionService

            secrets = await repo.get_all_secrets_for_inject(account_id)
            enc = EncryptionService(settings.encryption_key)
            for secret in secrets:
                try:
                    extra_env[secret.name] = enc.decrypt(secret.value_encrypted)
                except Exception:
                    pass
        except Exception:
            pass

        runner = FunctionRunner(
            timeout_seconds=settings.function_execution_timeout_seconds,
            stdout_max_bytes=settings.function_stdout_max_bytes,
        )
        result: InvokeResult = runner.invoke(
            env_path=version.env_path,
            source_files=dict(version.source_files or {}),
            entrypoint=fn.entrypoint or "handler.py",
            request_payload=request_payload,
            extra_env=extra_env,
        )

        body_out = result.body
        if isinstance(body_out, str):
            body_out = truncate_text(body_out, 8192)

        execution = FunctionExecutionModel(
            id=result.execution_id,
            function_id=fn.id,
            version_id=version.id,
            status=result.status,
            http_status=result.http_status,
            duration_ms=result.duration_ms,
            request_data=redact_request_data(
                method=method,
                path=path,
                headers=headers,
                query={},
                body=body,
            ),
            response_body=body_out,
            stdout=result.stdout,
            stderr=result.stderr,
            error_message=result.error_message,
            used_admin_client=result.used_admin_client,
        )
        await repo.create_execution(execution)
        await session.commit()

        if result.status == "timeout":
            raise TimeoutError(result.error_message or "Function timed out")
        if result.status == "failed":
            raise RuntimeError(result.error_message or "Function failed")

        return {
            "execution_id": result.execution_id,
            "http_status": result.http_status,
            "body": result.body,
            "status": result.status,
            "duration_ms": result.duration_ms,
        }
