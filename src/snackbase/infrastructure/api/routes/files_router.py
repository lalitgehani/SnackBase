"""File storage API endpoints for uploading and downloading files."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services.file_storage_service import FileStorageService
from snackbase.infrastructure.api.dependencies import CurrentUser, get_current_user
from snackbase.infrastructure.api.schemas.file_schemas import (
    FileMetadataResponse,
    FileUploadResponse,
)
from snackbase.infrastructure.persistence.database import get_db_session

logger = get_logger(__name__)

router = APIRouter(tags=["files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a file to storage. Returns file metadata including path for use in records.",
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FileUploadResponse:
    """Upload a file to storage."""
    account_id = current_user.account_id

    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"

    content = await file.read()
    size = len(content)

    storage_service = FileStorageService()

    try:
        from io import BytesIO

        file_metadata = await storage_service.save_file(
            session=db,
            account_id=account_id,
            file_content=BytesIO(content),
            filename=filename,
            mime_type=mime_type,
            size=size,
        )

        logger.info(
            "File uploaded successfully",
            account_id=account_id,
            filename=filename,
            size=size,
            user_id=current_user.user_id,
        )

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
    response_class=FileResponse,
    response_model=None,
    summary="Download a file",
    description="Download a file from storage. Requires authentication and proper permissions.",
)
async def download_file(
    file_path: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FileResponse | RedirectResponse:
    """Download a file from storage."""
    account_id = current_user.account_id
    storage_service = FileStorageService()

    try:
        mode, result = await storage_service.get_download_info(db, account_id, file_path)

        logger.info(
            "File downloaded",
            account_id=account_id,
            file_path=file_path,
            user_id=current_user.user_id,
            mode=mode,
        )

        if mode == "redirect":
            return RedirectResponse(url=result, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

        return FileResponse(
            path=result,
            filename=file_path.split("/")[-1],
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
