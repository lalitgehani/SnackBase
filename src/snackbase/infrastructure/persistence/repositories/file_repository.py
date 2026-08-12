"""File repository for the upload registry."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import FileModel


class FileRepository:
    """Repository for stored-file registry operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    async def create(self, file: FileModel) -> FileModel:
        """Register a stored file.

        Args:
            file: File model to persist.

        Returns:
            The persisted model.
        """
        self._session.add(file)
        await self._session.flush()
        return file

    async def get_by_path(self, account_id: str, path: str) -> FileModel | None:
        """Get a registered file by its storage path within an account.

        Scoped by account so a path from another tenant cannot be resolved even
        if the caller somehow knows it.

        Args:
            account_id: The account the caller is acting in.
            path: The storage path as handed to clients.

        Returns:
            File model if found, None otherwise.
        """
        result = await self._session.execute(
            select(FileModel).where(
                FileModel.account_id == account_id,
                FileModel.path == path,
            )
        )
        return result.scalar_one_or_none()
