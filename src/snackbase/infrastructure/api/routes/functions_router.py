"""Management API for Functions: CRUD, deploy, executions, secrets, grants, stats."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.function_schemas import (
    FunctionBodyResponse,
    FunctionCreateRequest,
    FunctionDeployRequest,
    FunctionDeployResponse,
    FunctionExecutionListResponse,
    FunctionExecutionResponse,
    FunctionGrantsUpdateRequest,
    FunctionListResponse,
    FunctionResponse,
    FunctionSecretListResponse,
    FunctionSecretResponse,
    FunctionSecretUpsertRequest,
    FunctionStatsResponse,
    FunctionTestRequest,
    FunctionUpdateRequest,
    FunctionVersionListResponse,
    FunctionVersionResponse,
)
from snackbase.infrastructure.functions.env_builder import (
    EnvBuildError,
    build_function_env,
    compute_version_sha,
    remove_function_env,
    total_source_bytes,
)
from snackbase.infrastructure.functions.pin_parser import PinParseError, parse_dependencies
from snackbase.infrastructure.functions.source_paths import SourcePathError, validate_source_files
from snackbase.infrastructure.functions.syntax_preflight import (
    SyntaxPreflightError,
    validate_python_syntax,
)
from snackbase.infrastructure.persistence.models.function import (
    FunctionModel,
    FunctionSecretModel,
    FunctionVersionModel,
)
from snackbase.infrastructure.persistence.repositories.function_repository import (
    FunctionRepository,
)
from snackbase.infrastructure.security.encryption import EncryptionService

router = APIRouter(tags=["Functions"])
logger = get_logger(__name__)


def get_function_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionRepository:
    return FunctionRepository(session)


FunctionRepo = Annotated[FunctionRepository, Depends(get_function_repository)]


def _build_function_response(fn: FunctionModel) -> FunctionResponse:
    grants = fn.grants or {}
    return FunctionResponse(
        id=fn.id,
        account_id=fn.account_id,
        slug=fn.slug,
        name=fn.name,
        description=fn.description,
        entrypoint=fn.entrypoint,
        auth_required=fn.auth_required,
        enabled=fn.enabled,
        status=fn.status,
        active_version_id=fn.active_version_id,
        grants=grants,
        created_by=fn.created_by,
        created_at=fn.created_at,
        updated_at=fn.updated_at,
    )


def _build_version_response(v: FunctionVersionModel) -> FunctionVersionResponse:
    return FunctionVersionResponse(
        id=v.id,
        function_id=v.function_id,
        version=v.version,
        dependencies=list(v.dependencies or []),
        sha256=v.sha256,
        env_path=v.env_path,
        created_by=v.created_by,
        created_at=v.created_at,
    )


def _require_functions_write(user: AuthenticatedUser) -> None:
    """Gate manage mutations: account admin/owner or functions:write scope."""
    role = (user.role or "").lower()
    if role in {"admin", "owner", "superadmin", "account_admin"}:
        return
    scopes = set(user.scopes or [])
    if "functions:write" in scopes:
        return
    # Superadmin account always allowed
    if user.account_id == "00000000-0000-0000-0000-000000000000":
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="functions:write permission required",
    )


def _require_secrets_write(user: AuthenticatedUser) -> None:
    role = (user.role or "").lower()
    if role in {"admin", "owner", "superadmin", "account_admin"}:
        return
    scopes = set(user.scopes or [])
    if "secrets:write" in scopes or "functions:write" in scopes:
        return
    if user.account_id == "00000000-0000-0000-0000-000000000000":
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="secrets:write permission required",
    )


async def _get_function_or_404(
    repo: FunctionRepository,
    account_id: str,
    slug: str,
    *,
    include_removed: bool = False,
) -> FunctionModel:
    fn = await repo.get_by_slug(account_id, slug, include_removed=include_removed)
    if not fn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    return fn


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FunctionResponse)
async def create_function(
    data: FunctionCreateRequest,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionResponse:
    _require_functions_write(current_user)
    settings = get_settings()
    count = await repo.count_for_account(current_user.account_id)
    if count >= settings.max_functions_per_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Account has reached the maximum of "
                f"{settings.max_functions_per_account} functions"
            ),
        )
    existing = await repo.get_by_slug(current_user.account_id, data.slug, include_removed=True)
    if existing and existing.status != "REMOVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Function with slug '{data.slug}' already exists",
        )
    if existing and existing.status == "REMOVED":
        # Reactivate soft-deleted
        existing.name = data.name
        existing.description = data.description
        existing.auth_required = data.auth_required
        existing.entrypoint = data.entrypoint
        existing.enabled = True
        existing.status = "ACTIVE"
        existing.grants = {}
        await repo.update(existing)
        await session.commit()
        await session.refresh(existing)
        return _build_function_response(existing)

    fn = FunctionModel(
        account_id=current_user.account_id,
        slug=data.slug,
        name=data.name,
        description=data.description,
        auth_required=data.auth_required,
        entrypoint=data.entrypoint,
        enabled=True,
        status="ACTIVE",
        grants={},
        created_by=current_user.user_id,
    )
    await repo.create(fn)
    await session.commit()
    await session.refresh(fn)
    logger.info("Function created", slug=fn.slug, account_id=fn.account_id)
    return _build_function_response(fn)


@router.get("", response_model=FunctionListResponse)
async def list_functions(
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    enabled: bool | None = None,
) -> FunctionListResponse:
    items, total = await repo.list_for_account(
        current_user.account_id,
        enabled=enabled,
        offset=offset,
        limit=limit,
    )
    return FunctionListResponse(
        items=[_build_function_response(i) for i in items],
        total=total,
    )


@router.get("/{slug}", response_model=FunctionResponse)
async def get_function(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
) -> FunctionResponse:
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    return _build_function_response(fn)


@router.patch("/{slug}", response_model=FunctionResponse)
async def update_function(
    slug: str,
    data: FunctionUpdateRequest,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionResponse:
    _require_functions_write(current_user)
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    if data.name is not None:
        fn.name = data.name
    if data.description is not None:
        fn.description = data.description
    if data.auth_required is not None:
        fn.auth_required = data.auth_required
    if data.enabled is not None:
        fn.enabled = data.enabled
    if data.status is not None:
        fn.status = data.status
        if data.status == "REMOVED":
            fn.enabled = False
    if data.entrypoint is not None:
        fn.entrypoint = data.entrypoint
    await repo.update(fn)
    await session.commit()
    await session.refresh(fn)
    return _build_function_response(fn)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_function(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    _require_functions_write(current_user)
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    await repo.soft_delete(fn)
    await session.commit()


# ---------------------------------------------------------------------------
# Deploy / versions / body
# ---------------------------------------------------------------------------


@router.post("/{slug}/deploy", response_model=FunctionDeployResponse)
async def deploy_function(
    slug: str,
    data: FunctionDeployRequest,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionDeployResponse:
    _require_functions_write(current_user)
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    settings = get_settings()

    if not data.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deploy requires at least one file in 'files'",
        )

    entrypoint = data.entrypoint or fn.entrypoint or "handler.py"
    try:
        entrypoint = validate_source_files(data.files, entrypoint)
    except SourcePathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        validate_python_syntax(data.files)
    except SyntaxPreflightError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    source_bytes = total_source_bytes(data.files)
    if source_bytes > settings.max_function_source_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Source exceeds max_function_source_bytes "
                f"({source_bytes} > {settings.max_function_source_bytes})"
            ),
        )

    requirements_txt = data.files.get("requirements.txt")
    try:
        pins = parse_dependencies(
            data.dependencies,
            requirements_txt=requirements_txt,
            mode=settings.function_dependency_mode,
            allowlist=settings.function_dependency_allowlist,
        )
    except PinParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    version_sha = compute_version_sha(data.files, pins)
    try:
        env_path = build_function_env(
            base_path=settings.function_env_base_path,
            account_id=fn.account_id,
            function_id=fn.id,
            version_sha=version_sha,
            dependencies=pins,
        )
    except EnvBuildError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dependency install failed: {exc}. {exc.stderr}",
        ) from exc

    version_num = await repo.next_version_number(fn.id)
    version = FunctionVersionModel(
        id=str(uuid.uuid4()),
        function_id=fn.id,
        version=version_num,
        source_files=data.files,
        dependencies=pins,
        sha256=version_sha,
        env_path=str(env_path),
        created_by=current_user.user_id,
    )
    await repo.create_version(version)
    fn.entrypoint = entrypoint
    await repo.set_active_version(fn, version.id)

    # GC old versions
    old = await repo.list_old_versions(fn.id, settings.max_function_versions_retained)
    for old_v in old:
        if old_v.id == fn.active_version_id:
            continue
        remove_function_env(old_v.env_path)
        await repo.delete_version(old_v)

    await session.commit()
    await session.refresh(fn)
    await session.refresh(version)

    logger.info(
        "Function deployed",
        slug=fn.slug,
        version=version.version,
        sha256=version.sha256,
        account_id=fn.account_id,
        actor_id=current_user.user_id,
    )
    from snackbase.infrastructure.functions.audit import emit_function_audit

    await emit_function_audit(
        session,
        account_id=fn.account_id,
        actor_id=current_user.user_id,
        actor_email=getattr(current_user, "email", None),
        operation="DEPLOY",
        function_id=fn.id,
        details={"slug": fn.slug, "version": version.version, "sha256": version.sha256},
    )
    await session.commit()

    return FunctionDeployResponse(
        function=_build_function_response(fn),
        version=_build_version_response(version),
    )


@router.get("/{slug}/versions", response_model=FunctionVersionListResponse)
async def list_versions(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> FunctionVersionListResponse:
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    items, total = await repo.list_versions(fn.id, offset=offset, limit=limit)
    return FunctionVersionListResponse(
        items=[_build_version_response(i) for i in items],
        total=total,
    )


@router.get("/{slug}/body", response_model=FunctionBodyResponse)
async def get_body(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    version_id: str | None = None,
) -> FunctionBodyResponse:
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    vid = version_id or fn.active_version_id
    if not vid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active version")
    version = await repo.get_version(vid)
    if not version or version.function_id != fn.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return FunctionBodyResponse(
        version_id=version.id,
        version=version.version,
        entrypoint=fn.entrypoint,
        files=dict(version.source_files or {}),
        dependencies=list(version.dependencies or []),
        sha256=version.sha256,
    )


@router.post(
    "/{slug}/versions/{version_id}/activate",
    response_model=FunctionResponse,
)
async def activate_version(
    slug: str,
    version_id: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionResponse:
    _require_functions_write(current_user)
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    version = await repo.get_version(version_id)
    if not version or version.function_id != fn.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    if not version.env_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version environment is missing; redeploy required",
        )
    await repo.set_active_version(fn, version.id)
    from snackbase.infrastructure.functions.audit import emit_function_audit

    await emit_function_audit(
        session,
        account_id=fn.account_id,
        actor_id=current_user.user_id,
        actor_email=getattr(current_user, "email", None),
        operation="ACTIVATE",
        function_id=fn.id,
        details={"slug": fn.slug, "version_id": version_id, "version": version.version},
    )
    await session.commit()
    await session.refresh(fn)
    return _build_function_response(fn)


@router.patch("/{slug}/grants", response_model=FunctionResponse)
async def update_grants(
    slug: str,
    data: FunctionGrantsUpdateRequest,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionResponse:
    _require_functions_write(current_user)
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    # Store grants as {"capabilities": [...]} for forward compatibility
    fn.grants = {"capabilities": list(data.grants)}
    await repo.update(fn)
    from snackbase.infrastructure.functions.audit import emit_function_audit

    await emit_function_audit(
        session,
        account_id=fn.account_id,
        actor_id=current_user.user_id,
        actor_email=getattr(current_user, "email", None),
        operation="GRANTS",
        function_id=fn.id,
        details={"slug": fn.slug, "grants": list(data.grants)},
    )
    await session.commit()
    await session.refresh(fn)
    return _build_function_response(fn)


@router.get("/{slug}/stats", response_model=FunctionStatsResponse)
async def function_stats(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    range: Literal["1h", "24h", "7d"] = Query("24h"),
) -> FunctionStatsResponse:
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    now = datetime.now(UTC)
    delta = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}[range]
    stats = await repo.execution_stats(fn.id, since=now - delta)
    return FunctionStatsResponse(
        total=stats["total"],
        by_status=stats["by_status"],
        p50_ms=stats["p50_ms"],
        p95_ms=stats["p95_ms"],
        range=range,
    )


@router.get("/{slug}/executions", response_model=FunctionExecutionListResponse)
async def list_executions(
    slug: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> FunctionExecutionListResponse:
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    items, total = await repo.list_executions(fn.id, offset=offset, limit=limit)
    return FunctionExecutionListResponse(
        items=[FunctionExecutionResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/{slug}/test")
async def test_function(
    slug: str,
    data: FunctionTestRequest,
    request: Request,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Invoke the active version with a synthetic request (management test sheet)."""
    fn = await _get_function_or_404(repo, current_user.account_id, slug)
    if not fn.active_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Function has no active version; deploy first",
        )
    version = await repo.get_version(fn.active_version_id)
    if not version or not version.env_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active version environment missing",
        )

    from snackbase.infrastructure.api.routes.function_dispatcher import (
        build_invoke_env,
        run_and_log_execution,
    )

    settings = get_settings()
    auth_ctx = {
        "user_id": current_user.user_id,
        "email": getattr(current_user, "email", None),
        "account_id": current_user.account_id,
        "role": getattr(current_user, "role", None),
    }
    request_payload = {
        "method": data.method.upper(),
        "path": data.path or "/",
        "headers": data.headers,
        "query": data.query,
        "json": data.body,
        "body": data.body,
        "auth": auth_ctx,
    }
    extra_env = await build_invoke_env(
        request=request,
        fn=fn,
        account_id=fn.account_id,
        auth=auth_ctx,
        repo=repo,
        caller_token=_extract_bearer(request),
    )
    result = await run_and_log_execution(
        repo=repo,
        session=session,
        fn=fn,
        version=version,
        request_payload=request_payload,
        extra_env=extra_env,
        settings=settings,
    )
    return {
        "execution_id": result.execution_id,
        "status": result.status,
        "http_status": result.http_status,
        "headers": result.headers,
        "body": result.body,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error_message": result.error_message,
        "duration_ms": result.duration_ms,
    }


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


# ---------------------------------------------------------------------------
# Secrets (also mounted at /api/v1/function-secrets)
# ---------------------------------------------------------------------------


@router.get("/secrets/__list", include_in_schema=False)
async def _secrets_placeholder() -> None:
    """Placeholder to keep path order; real secrets routes are separate."""
    return None


secrets_router = APIRouter(tags=["Function Secrets"])


@secrets_router.get("", response_model=FunctionSecretListResponse)
async def list_secrets(
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
) -> FunctionSecretListResponse:
    items = await repo.list_secrets(current_user.account_id)
    return FunctionSecretListResponse(
        items=[FunctionSecretResponse.model_validate(i) for i in items],
        total=len(items),
    )


@secrets_router.post("", response_model=FunctionSecretResponse, status_code=status.HTTP_201_CREATED)
async def upsert_secret(
    data: FunctionSecretUpsertRequest,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FunctionSecretResponse:
    _require_secrets_write(current_user)
    settings = get_settings()
    count = await repo.count_secrets(current_user.account_id)
    existing = await repo.get_secret(current_user.account_id, data.name)
    if not existing and count >= settings.max_function_secrets_per_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum function secrets per account reached",
        )
    if len(data.value.encode("utf-8")) > 48 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secret value exceeds 48 KiB",
        )
    enc = EncryptionService(settings.encryption_key)
    encrypted = enc.encrypt(data.value)
    secret = FunctionSecretModel(
        account_id=current_user.account_id,
        name=data.name,
        value_encrypted=encrypted,
    )
    saved = await repo.upsert_secret(secret)
    await session.commit()
    await session.refresh(saved)
    return FunctionSecretResponse.model_validate(saved)


@secrets_router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    name: str,
    current_user: AuthenticatedUser,
    repo: FunctionRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    _require_secrets_write(current_user)
    deleted = await repo.delete_secret(current_user.account_id, name)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    await session.commit()
