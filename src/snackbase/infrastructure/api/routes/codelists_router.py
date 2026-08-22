"""REST API for first-class codelists.

- Authenticated users: list codelists, read effective values
- Account admins: private lists, extensions (when extensible), overrides
- Superadmins: system lists/values/labels management; optional account preview
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services.codelist_service import (
    CodelistConflictError,
    CodelistError,
    CodelistForbiddenError,
    CodelistNotFoundError,
    CodelistService,
    CodelistValidationError,
    CodelistValueNotFoundError,
)
from snackbase.infrastructure.api.dependencies import (
    SYSTEM_ACCOUNT_ID,
    AuthenticatedUser,
    get_db_session,
    require_superadmin,
)
from snackbase.infrastructure.api.schemas.codelist_schemas import (
    CodelistCreateRequest,
    CodelistPackageImportRequest,
    CodelistResponse,
    CodelistUpdateRequest,
    CodelistValueCreateRequest,
    CodelistValueResponse,
    CodelistValueUpdateRequest,
    EffectiveValueResponse,
    LabelResponse,
    LabelUpsertRequest,
    MessageResponse,
    OverrideRequest,
    OverrideResponse,
)
from snackbase.infrastructure.auth.token_types import AuthenticatedUser as AuthUser

router = APIRouter(tags=["codelists"])
logger = get_logger(__name__)


def get_codelist_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CodelistService:
    return CodelistService(session)


CodelistSvc = Annotated[CodelistService, Depends(get_codelist_service)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _is_superadmin(user: AuthUser) -> bool:
    return user.account_id == SYSTEM_ACCOUNT_ID


def _is_account_admin(user: AuthUser) -> bool:
    return user.role == "admin" or _is_superadmin(user)


def _require_account_admin(user: AuthUser) -> None:
    if not _is_account_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account admin role required",
        )


def _map_error(exc: CodelistError) -> HTTPException:
    if isinstance(exc, CodelistNotFoundError) or isinstance(
        exc, CodelistValueNotFoundError
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, CodelistForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)
    if isinstance(exc, CodelistConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    if isinstance(exc, CodelistValidationError):
        code = getattr(exc, "code", "codelist_validation")
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if code in ("not_in_codelist", "invalid_code", "invalid_value_code")
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        return HTTPException(status_code=status_code, detail=exc.message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _codelist_response(model: Any) -> CodelistResponse:
    return CodelistResponse(
        id=model.id,
        code=model.code,
        name=model.name,
        description=model.description,
        definition=model.definition,
        scope=model.scope,
        account_id=model.account_id,
        is_system=model.is_system,
        is_extensible=model.is_extensible,
        is_active=model.is_active,
        is_builtin=model.is_builtin,
        external_code=model.external_code,
        version=model.version,
        metadata=model.metadata_,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _value_response(model: Any) -> CodelistValueResponse:
    from sqlalchemy import inspect as sa_inspect

    labels: list[LabelResponse] = []
    # Avoid async lazy-load of relationship when not eagerly loaded
    insp = sa_inspect(model)
    labels_loaded = "labels" not in insp.unloaded
    if labels_loaded and model.labels:
        labels = [
            LabelResponse(
                id=lb.id,
                value_id=lb.value_id,
                language=lb.language,
                label=lb.label,
                description=lb.description,
                is_preferred=lb.is_preferred,
            )
            for lb in model.labels
        ]
    return CodelistValueResponse(
        id=model.id,
        codelist_id=model.codelist_id,
        code=model.code,
        external_code=model.external_code,
        sort_order=model.sort_order,
        is_active=model.is_active,
        scope=model.scope,
        account_id=model.account_id,
        is_system=model.is_system,
        definition=model.definition,
        metadata=model.metadata_,
        labels=labels,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# ---------------------------------------------------------------------------
# Read paths (authenticated)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[CodelistResponse],
    summary="List codelists visible to caller",
)
async def list_codelists(
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    scope: str | None = Query(None, description="Filter: system | account"),
    active: bool = Query(False, description="If true, only active lists"),
) -> list[CodelistResponse]:
    account_id = current_user.account_id
    items = await svc.list_codelists(
        account_id=account_id,
        scope=scope,
        active_only=active,
    )
    return [_codelist_response(c) for c in items]


@router.get(
    "/{code}",
    response_model=CodelistResponse,
    summary="Get codelist metadata",
)
async def get_codelist(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
) -> CodelistResponse:
    try:
        model = await svc.get_codelist(code, account_id=current_user.account_id)
    except CodelistError as e:
        raise _map_error(e) from e
    # Private list isolation
    if not model.is_system and model.account_id != current_user.account_id:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Codelist not found"
            )
    return _codelist_response(model)


@router.get(
    "/{code}/values",
    response_model=list[EffectiveValueResponse],
    summary="List effective values for caller account",
)
async def get_effective_values(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    lang: str = Query("en", description="BCP-47 language for labels"),
    active: bool = Query(True, description="Exclude inactive when true"),
    account_id: str | None = Query(
        None,
        description="Superadmin only: preview effective set as another account",
    ),
) -> list[EffectiveValueResponse]:
    target_account = current_user.account_id
    if account_id is not None and account_id != current_user.account_id:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin may pass account_id for preview",
            )
        target_account = account_id

    try:
        values = await svc.get_effective_values(
            target_account,
            code,
            language=lang,
            include_inactive=not active,
        )
    except CodelistError as e:
        raise _map_error(e) from e

    return [
        EffectiveValueResponse(
            code=v.code,
            label=v.label,
            definition=v.definition,
            metadata=v.metadata,
            is_default=v.is_default,
            sort_order=v.sort_order,
            scope=v.scope,
            is_active=v.is_active,
            value_id=v.value_id,
        )
        for v in values
    ]


@router.get(
    "/{code}/values/{value_code}",
    response_model=EffectiveValueResponse,
    summary="Resolve a single value including inactive (historical display)",
)
async def resolve_value(
    code: str,
    value_code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    lang: str = Query("en"),
) -> EffectiveValueResponse:
    try:
        codelist = await svc.get_codelist(code, account_id=current_user.account_id)
        raw = await svc.repo.get_value_by_code(
            codelist.id, value_code, account_id=current_user.account_id
        )
        if raw is None:
            raise CodelistValueNotFoundError(f"Value '{value_code}' not found")
        label = await svc.resolve_label(
            code, value_code, lang, account_id=current_user.account_id, include_inactive=True
        )
    except CodelistError as e:
        raise _map_error(e) from e
    return EffectiveValueResponse(
        code=raw.code,
        label=label,
        definition=raw.definition,
        metadata=raw.metadata_,
        is_default=False,
        sort_order=raw.sort_order,
        scope=raw.scope,
        is_active=raw.is_active,
        value_id=raw.id,
    )


# ---------------------------------------------------------------------------
# Codelist management
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CodelistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a codelist",
)
async def create_codelist(
    body: CodelistCreateRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> CodelistResponse:
    if body.scope == "system":
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to create system codelists",
            )
        account_id = SYSTEM_ACCOUNT_ID
    else:
        _require_account_admin(current_user)
        if _is_superadmin(current_user):
            # Superadmin creating account list needs explicit account context —
            # default to system is wrong; require account scope with own account
            # For superadmin, account-scope creates under system unless intended;
            # MVP: account-scope always uses caller's account_id
            account_id = current_user.account_id
        else:
            account_id = current_user.account_id

    try:
        model = await svc.create_codelist(
            code=body.code,
            name=body.name,
            account_id=account_id,
            scope=body.scope,
            description=body.description,
            definition=body.definition,
            is_extensible=body.is_extensible,
            is_active=body.is_active,
            external_code=body.external_code,
            version=body.version,
            metadata=body.metadata,
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e

    logger.info(
        "Codelist created",
        code=model.code,
        scope=model.scope,
        user_id=current_user.user_id,
        account_id=model.account_id,
    )
    return _codelist_response(model)


@router.patch(
    "/{code}",
    response_model=CodelistResponse,
    summary="Update codelist metadata",
)
async def update_codelist(
    code: str,
    body: CodelistUpdateRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> CodelistResponse:
    try:
        model = await svc.get_codelist(code, account_id=current_user.account_id)
    except CodelistError as e:
        raise _map_error(e) from e

    if model.is_system:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to update system codelists",
            )
    else:
        _require_account_admin(current_user)
        if model.account_id != current_user.account_id and not _is_superadmin(
            current_user
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Codelist not found"
            )

    try:
        updated = await svc.update_codelist(
            code,
            account_id=current_user.account_id,
            name=body.name,
            description=body.description,
            definition=body.definition,
            is_extensible=body.is_extensible,
            is_active=body.is_active,
            external_code=body.external_code,
            version=body.version,
            metadata=body.metadata,
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e
    return _codelist_response(updated)


@router.delete(
    "/{code}",
    response_model=CodelistResponse,
    summary="Soft-deactivate (or hard-delete when allowed) a codelist",
)
async def delete_codelist(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
    hard: bool = Query(False, description="Hard delete when allowed"),
) -> CodelistResponse:
    try:
        model = await svc.get_codelist(code, account_id=current_user.account_id)
    except CodelistError as e:
        raise _map_error(e) from e

    if model.is_system:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to delete system codelists",
            )
    else:
        _require_account_admin(current_user)
        if model.account_id != current_user.account_id and not _is_superadmin(
            current_user
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Codelist not found"
            )

    try:
        result = await svc.delete_codelist(
            code, account_id=current_user.account_id, hard=hard
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e
    return _codelist_response(result)


# ---------------------------------------------------------------------------
# Value management
# ---------------------------------------------------------------------------


@router.post(
    "/{code}/manage/values",
    response_model=CodelistValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a value (system or account extension)",
)
async def create_value(
    code: str,
    body: CodelistValueCreateRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> CodelistValueResponse:
    try:
        codelist = await svc.get_codelist(code, account_id=current_user.account_id)
    except CodelistError as e:
        raise _map_error(e) from e

    as_system = False
    if codelist.is_system:
        # System value requires superadmin; extension requires account admin + extensible
        if _is_superadmin(current_user):
            as_system = True
            account_id = SYSTEM_ACCOUNT_ID
        else:
            _require_account_admin(current_user)
            as_system = False
            account_id = current_user.account_id
    else:
        _require_account_admin(current_user)
        if codelist.account_id != current_user.account_id and not _is_superadmin(
            current_user
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Codelist not found"
            )
        account_id = codelist.account_id
        as_system = False

    try:
        value = await svc.add_value(
            code,
            code=body.code,
            account_id=account_id,
            definition=body.definition,
            sort_order=body.sort_order,
            is_active=body.is_active,
            external_code=body.external_code,
            metadata=body.metadata,
            as_system=as_system,
        )
        if body.labels:
            for lb in body.labels:
                await svc.set_label(
                    value.id,
                    lb.language,
                    lb.label,
                    description=lb.description,
                    is_preferred=lb.is_preferred,
                )
            value = await svc.repo.get_value_by_id(value.id)
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e

    logger.info(
        "Codelist value created",
        codelist=code,
        value_code=body.code,
        user_id=current_user.user_id,
    )
    assert value is not None
    return _value_response(value)


@router.patch(
    "/{code}/manage/values/{value_code}",
    response_model=CodelistValueResponse,
    summary="Update a value",
)
async def update_value(
    code: str,
    value_code: str,
    body: CodelistValueUpdateRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> CodelistValueResponse:
    try:
        codelist = await svc.get_codelist(code, account_id=current_user.account_id)
        raw = await svc.repo.get_value_by_code(
            codelist.id, value_code, account_id=current_user.account_id
        )
        if raw is None:
            raise CodelistValueNotFoundError(f"Value '{value_code}' not found")
        if raw.is_system and not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to update system values",
            )
        if not raw.is_system:
            _require_account_admin(current_user)
            if raw.account_id != current_user.account_id and not _is_superadmin(
                current_user
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Value not found"
                )

        updated = await svc.update_value(
            code,
            value_code,
            account_id=raw.account_id,
            definition=body.definition,
            sort_order=body.sort_order,
            is_active=body.is_active,
            external_code=body.external_code,
            metadata=body.metadata,
        )
        await session.commit()
        refreshed = await svc.repo.get_value_by_id(updated.id)
    except CodelistError as e:
        raise _map_error(e) from e
    assert refreshed is not None
    return _value_response(refreshed)


@router.post(
    "/{code}/manage/values/{value_code}/labels",
    response_model=list[LabelResponse],
    summary="Upsert labels for a value",
)
async def upsert_labels(
    code: str,
    value_code: str,
    body: list[LabelUpsertRequest],
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> list[LabelResponse]:
    try:
        codelist = await svc.get_codelist(code, account_id=current_user.account_id)
        raw = await svc.repo.get_value_by_code(
            codelist.id, value_code, account_id=current_user.account_id
        )
        if raw is None:
            raise CodelistValueNotFoundError(f"Value '{value_code}' not found")
        if raw.is_system and not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to update system value labels",
            )
        if not raw.is_system:
            _require_account_admin(current_user)

        results = await svc.bulk_upsert_labels(
            raw.id,
            [lb.model_dump() for lb in body],
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e
    return [
        LabelResponse(
            id=r.id,
            value_id=r.value_id,
            language=r.language,
            label=r.label,
            description=r.description,
            is_preferred=r.is_preferred,
        )
        for r in results
    ]


@router.get(
    "/{code}/manage/values",
    response_model=list[CodelistValueResponse],
    summary="List raw values for management (includes inactive when requested)",
)
async def list_manage_values(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    include_inactive: bool = Query(True),
) -> list[CodelistValueResponse]:
    try:
        values = await svc.list_values(
            code,
            account_id=current_user.account_id,
            include_inactive=include_inactive,
        )
    except CodelistError as e:
        raise _map_error(e) from e
    # Filter private extensions from other accounts
    result = []
    for v in values:
        if not v.is_system and v.account_id != current_user.account_id:
            if not _is_superadmin(current_user):
                continue
        result.append(_value_response(v))
    return result


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------


@router.put(
    "/{code}/values/{value_code}/override",
    response_model=OverrideResponse,
    summary="Set account override for a value",
)
async def set_override(
    code: str,
    value_code: str,
    body: OverrideRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
    account_id: str | None = Query(
        None, description="Superadmin: target account for override"
    ),
) -> OverrideResponse:
    _require_account_admin(current_user)
    target = current_user.account_id
    if account_id is not None and account_id != current_user.account_id:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin may set overrides for another account",
            )
        target = account_id
    # Superadmin default account is system — require explicit account for overrides
    if _is_superadmin(current_user) and target == SYSTEM_ACCOUNT_ID and account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superadmin must pass account_id when setting overrides",
        )

    try:
        ov = await svc.set_override(
            code,
            value_code,
            account_id=target,
            visibility=body.visibility,
            is_default=body.is_default,
            sort_order=body.sort_order,
            metadata_override=body.metadata_override,
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e

    logger.info(
        "Codelist override set",
        codelist=code,
        value_code=value_code,
        account_id=target,
        visibility=body.visibility,
        user_id=current_user.user_id,
    )
    return OverrideResponse(
        id=ov.id,
        account_id=ov.account_id,
        codelist_id=ov.codelist_id,
        value_id=ov.value_id,
        visibility=ov.visibility,
        is_default=ov.is_default,
        sort_order=ov.sort_order,
        metadata_override=ov.metadata_override,
    )


@router.delete(
    "/{code}/values/{value_code}/override",
    response_model=MessageResponse,
    summary="Clear account override for a value",
)
async def clear_override(
    code: str,
    value_code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
    account_id: str | None = Query(None),
) -> MessageResponse:
    _require_account_admin(current_user)
    target = current_user.account_id
    if account_id is not None and account_id != current_user.account_id:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin may clear overrides for another account",
            )
        target = account_id
    if _is_superadmin(current_user) and target == SYSTEM_ACCOUNT_ID and account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superadmin must pass account_id when clearing overrides",
        )

    try:
        await svc.clear_override(code, value_code, account_id=target)
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e
    return MessageResponse(message="Override cleared")


@router.get(
    "/{code}/overrides",
    response_model=list[OverrideResponse],
    summary="List overrides for account+codelist",
)
async def list_overrides(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    account_id: str | None = Query(None),
) -> list[OverrideResponse]:
    _require_account_admin(current_user)
    target = current_user.account_id
    if account_id is not None and account_id != current_user.account_id:
        if not _is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin may list overrides for another account",
            )
        target = account_id
    if _is_superadmin(current_user) and target == SYSTEM_ACCOUNT_ID and account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superadmin must pass account_id when listing overrides",
        )
    try:
        items = await svc.list_overrides(code, account_id=target)
    except CodelistError as e:
        raise _map_error(e) from e
    return [
        OverrideResponse(
            id=o.id,
            account_id=o.account_id,
            codelist_id=o.codelist_id,
            value_id=o.value_id,
            visibility=o.visibility,
            is_default=o.is_default,
            sort_order=o.sort_order,
            metadata_override=o.metadata_override,
        )
        for o in items
    ]


# ---------------------------------------------------------------------------
# Import / export (superadmin system packages)
# ---------------------------------------------------------------------------


@router.get(
    "/{code}/export",
    summary="Export codelist package (JSON)",
)
async def export_codelist(
    code: str,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
) -> dict[str, Any]:
    try:
        model = await svc.get_codelist(code, account_id=current_user.account_id)
        if model.is_system and not _is_superadmin(current_user):
            # Account users can export own private lists; system export is superadmin
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin required to export system codelists",
            )
        if not model.is_system:
            _require_account_admin(current_user)
        return await svc.export_codelist_package(
            code, account_id=current_user.account_id
        )
    except CodelistError as e:
        raise _map_error(e) from e


@router.post(
    "/import",
    response_model=CodelistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import codelist package (superadmin system scope)",
    dependencies=[Depends(require_superadmin)],
)
async def import_codelist(
    body: CodelistPackageImportRequest,
    current_user: AuthenticatedUser,
    svc: CodelistSvc,
    session: DbSession,
) -> CodelistResponse:
    try:
        model = await svc.import_codelist_package(
            body.package, as_system=True, account_id=SYSTEM_ACCOUNT_ID
        )
        await session.commit()
    except CodelistError as e:
        raise _map_error(e) from e
    return _codelist_response(model)
