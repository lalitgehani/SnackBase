"""File storage API endpoints for uploading and downloading files."""

import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services.file_storage_service import (
    SNIFF_BYTES,
    buffer_upload_within_limit,
    detect_mime_type,
    size_limit_error,
)
from snackbase.infrastructure.api.dependencies import (
    SYSTEM_ACCOUNT_ID,
    AuthContext,
    AuthorizationContext,
    CurrentUser,
    get_current_user,
)
from snackbase.infrastructure.api.middleware import check_collection_permission
from snackbase.infrastructure.api.schemas.file_schemas import (
    FileMetadataResponse,
    FileUploadResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import FileModel
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    FileRepository,
    RecordRepository,
)
from snackbase.infrastructure.persistence.repositories.record_repository import RuleFilter
from snackbase.infrastructure.storage.storage_service import StorageService

logger = get_logger(__name__)

router = APIRouter(tags=["files"])

# A multipart body carries part headers and boundaries on top of the file
# itself, so a body a little over the cap can still hold a legal file. Only a
# body that cannot possibly be within the cap is refused up front; anything
# that slips past is caught by the bounded read.
_MULTIPART_ENVELOPE_ALLOWANCE = 8 * 1024


def _declared_body_size(request: Request) -> int | None:
    """Return the request's declared Content-Length, if it sent a usable one."""
    raw = request.headers.get("content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


async def _readable_through_a_record(
    auth_context: AuthorizationContext,
    account_id: str,
    file_path: str,
    db: AsyncSession,
) -> bool:
    """Return True if a record the caller may read references ``file_path``.

    A file's permissions are the permissions of the record that carries it: the
    collection rule governing the record has to govern its attachment too, or
    the rule is only as strong as the secrecy of a path — and paths are not
    secret. They come back in record payloads, in webhook bodies and in exports.

    Every collection with a ``file`` field is considered, because the same file
    may be referenced from more than one, and the first collection whose view
    rule admits the caller settles it.
    """
    collection_repo = CollectionRepository(db)
    record_repo = RecordRepository(db)

    for collection in await collection_repo.list_all():
        try:
            schema = json.loads(collection.schema)
        except (json.JSONDecodeError, TypeError):
            continue

        file_fields = [f["name"] for f in schema if f.get("type") == "file" and f.get("name")]
        if not file_fields:
            continue

        try:
            rule_filter = await check_collection_permission(
                auth_context=auth_context,
                collection=collection.name,
                operation="view",
                session=db,
            )
        except HTTPException:
            # Locked, or no rules: this collection cannot grant the caller
            # anything, so move on rather than failing the whole request.
            continue

        # Field names come from the collection schema, which is validated when
        # the collection is defined — never from the request.
        matches = " OR ".join(f'r."{field}" LIKE :file_path_like' for field in file_fields)
        reference_filter = RuleFilter(
            sql=f"({matches})", params={"file_path_like": f"%{file_path}%"}
        )

        _, total = await record_repo.find_all(
            collection_name=collection.name,
            account_id=account_id,
            schema=schema,
            limit=1,
            user_filter=reference_filter,
            rule_filter=rule_filter,
        )
        if total:
            return True

    return False


async def _authorize_download(
    auth_context: AuthorizationContext,
    current_user: CurrentUser,
    file_path: str,
    db: AsyncSession,
) -> None:
    """Ensure the caller has a claim to this file, not merely its path.

    Raises:
        HTTPException: 403 if the caller has no claim to the file.
    """
    if current_user.account_id == SYSTEM_ACCOUNT_ID:
        return

    registered = await FileRepository(db).get_by_path(current_user.account_id, file_path)

    # The uploader supplied the bytes, so they keep access regardless of where
    # the file was later attached — this is also what makes the ordinary
    # upload-then-attach flow work before any record exists.
    if registered is not None and registered.uploaded_by == current_user.user_id:
        return

    if await _readable_through_a_record(
        auth_context, current_user.account_id, file_path, db
    ):
        return

    logger.warning(
        "File download denied: no claim to the file",
        account_id=current_user.account_id,
        user_id=current_user.user_id,
        file_path=file_path,
        registered=registered is not None,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this file",
    )


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a file to storage. Returns file metadata including path for use in records.",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="File to upload"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FileUploadResponse:
    """Upload a file to storage.

    The uploaded file is stored in the account's directory with a UUID-based filename.
    Returns metadata that should be stored in a record's file field.

    Requires authentication. File size and MIME type are validated against configured limits.

    The body is never read in one unbounded call: an obviously-too-large
    declaration is refused before reading anything, and the rest is consumed in
    bounded slices that abort as soon as the running total crosses the limit.
    """
    account_id = current_user.account_id

    # Get file info. The declared type is a claim to be checked against the
    # bytes, not an answer.
    filename = file.filename or "unnamed"
    declared_mime_type = file.content_type or "application/octet-stream"

    max_size = get_settings().max_file_size

    # Create storage service (resolves active configured provider)
    storage_service = StorageService(db)

    try:
        declared = _declared_body_size(request)
        if declared is not None and declared > max_size + _MULTIPART_ENVELOPE_ALLOWANCE:
            raise size_limit_error(declared, max_size)

        content, size = await buffer_upload_within_limit(file.read, max_size)

        head = content.read(SNIFF_BYTES)
        content.seek(0)
        mime_type = detect_mime_type(head, declared_mime_type)

        # Save file (this validates size and MIME type, and names the stored
        # file from the detected type)
        file_metadata = await storage_service.save_file(
            account_id=account_id,
            file_content=content,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )

        logger.info(
            "File uploaded successfully",
            account_id=account_id,
            filename=filename,
            size=size,
            mime_type=mime_type,
            declared_mime_type=declared_mime_type,
            user_id=current_user.user_id,
        )

        # Register the stored object so a later download can be authorized
        # against who uploaded it and which record references it, rather than
        # against knowledge of the path.
        await FileRepository(db).create(
            FileModel(
                account_id=account_id,
                path=file_metadata.path,
                filename=file_metadata.filename,
                mime_type=file_metadata.mime_type,
                size=file_metadata.size,
                uploaded_by=current_user.user_id,
            )
        )
        await db.commit()

        return FileUploadResponse(
            success=True,
            file=FileMetadataResponse(
                filename=file_metadata.filename,
                size=file_metadata.size,
                mime_type=file_metadata.mime_type,
                path=file_metadata.path,
            ),
            message="File uploaded successfully",
        )

    except ValueError as e:
        logger.warning(
            "File upload validation failed",
            account_id=account_id,
            filename=filename,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "File upload failed",
            account_id=account_id,
            filename=filename,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )


@router.get(
    "/{file_path:path}",
    summary="Download a file",
    description="Download a file from storage. Requires authentication and proper permissions.",
)
async def download_file(
    file_path: str,
    auth_context: AuthContext,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Download a file from storage.

    The file path should be in the format: {account_id}/{uuid_filename}

    Requires authentication. The account boundary is enforced by the storage
    layer; on top of that a caller must have a claim to this particular file —
    either they uploaded it, or a record they are allowed to read references it.
    Knowing the path is not itself a claim.
    """
    account_id = current_user.account_id

    # Outside the try below: its `except Exception` would otherwise turn a
    # deliberate 403 into a 500.
    await _authorize_download(auth_context, current_user, file_path, db)

    # Create storage service (routes by file path/provider)
    storage_service = StorageService(db)

    try:
        stored_file = await storage_service.get_file(account_id, file_path)

        logger.info(
            "File downloaded",
            account_id=account_id,
            file_path=file_path,
            user_id=current_user.user_id,
        )

        if stored_file.local_path is not None:
            return FileResponse(
                path=str(stored_file.local_path),
                filename=stored_file.filename or stored_file.local_path.name,
                media_type=stored_file.mime_type,
            )

        if stored_file.content is None:
            raise RuntimeError("Storage provider returned an empty file response")

        download_name = stored_file.filename or "download"
        headers = {"Content-Disposition": f'attachment; filename="{download_name}"'}
        return Response(
            content=stored_file.content,
            media_type=stored_file.mime_type or "application/octet-stream",
            headers=headers,
        )

    except ValueError as e:
        logger.warning(
            "File download validation failed",
            account_id=account_id,
            file_path=file_path,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FileNotFoundError as e:
        logger.warning(
            "File not found",
            account_id=account_id,
            file_path=file_path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "File download failed",
            account_id=account_id,
            file_path=file_path,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        )
