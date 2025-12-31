"""Migration query service for read-only Alembic migration information.

Provides programmatic access to Alembic migration status and history.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class MigrationQueryService:
    """Service for querying Alembic migration information."""

    def __init__(
        self,
        alembic_ini_path: str = "alembic.ini",
        database_url: str | None = None,
        engine: AsyncEngine | None = None,
    ):
        """Initialize the migration query service.

        Args:
            alembic_ini_path: Path to the alembic.ini file.
            database_url: Optional database URL to override the one in alembic.ini.
            engine: Optional database engine to use for queries.
        """
        self.alembic_cfg = Config(alembic_ini_path)
        if database_url:
            self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        self.engine = engine
        self.script_dir = ScriptDirectory.from_config(self.alembic_cfg)

    async def get_all_revisions(self) -> list[dict[str, Any]]:
        """List all Alembic revisions from both core and dynamic directories.

        Returns:
            List of revision dictionaries with metadata.
        """
        revisions = []
        current_revision = await self.get_current_revision()
        current_rev_id = current_revision.get("revision") if current_revision else None

        # Get all revisions from the script directory
        for revision in self.script_dir.walk_revisions():
            # Determine if this is a dynamic migration
            module_path = revision.module.__file__ if revision.module else None
            is_dynamic = (
                any(path in module_path for path in ["dynamic", "sb_data/migrations"])
                if module_path
                else False
            )

            # Check if this revision is applied
            is_applied = False
            if current_rev_id:
                # Check if this revision is in the upgrade path to current
                is_applied = self._is_revision_applied(revision.revision, current_rev_id)

            # Check if this is the head revision
            is_head = revision.revision == self.script_dir.get_current_head()

            # Extract creation timestamp from the revision module
            created_at = self._extract_creation_timestamp(revision)

            revisions.append(
                {
                    "revision": revision.revision,
                    "description": revision.doc or "",
                    "down_revision": revision.down_revision,
                    "branch_labels": revision.branch_labels,
                    "is_applied": is_applied,
                    "is_head": is_head,
                    "is_dynamic": is_dynamic,
                    "created_at": created_at,
                }
            )

        # Sort by creation timestamp (newest first)
        revisions.sort(key=lambda x: x.get("created_at") or "", reverse=True)

        logger.debug(
            "Retrieved all revisions",
            total=len(revisions),
            current=current_rev_id,
        )

        return revisions

    async def get_current_revision(self) -> dict[str, Any] | None:
        """Get the current database revision.

        Returns:
            Current revision details or None if database is not initialized.
        """
        if not self.engine:
            logger.warning("No engine provided, cannot query current revision")
            return None

        try:
            async with self.engine.connect() as connection:
                # Run sync operation in the async context
                def get_revision(sync_conn):
                    context = MigrationContext.configure(sync_conn)
                    return context.get_current_revision()

                current_rev = await connection.run_sync(get_revision)

                if not current_rev:
                    logger.debug("No current revision found (database not initialized)")
                    return None

                # Get revision details from script directory
                revision_obj = self.script_dir.get_revision(current_rev)
                if not revision_obj:
                    logger.warning(
                        "Current revision not found in script directory",
                        revision=current_rev,
                    )
                    return {"revision": current_rev, "description": "", "created_at": None}

                created_at = self._extract_creation_timestamp(revision_obj)

                logger.debug("Retrieved current revision", revision=current_rev)

                return {
                    "revision": revision_obj.revision,
                    "description": revision_obj.doc or "",
                    "created_at": created_at,
                }

        except Exception as e:
            logger.error("Failed to get current revision", error=str(e))
            return None

    async def get_migration_history(self) -> list[dict[str, Any]]:
        """Get full migration history in chronological order.

        Returns:
            List of revisions in order from oldest to newest.
        """
        all_revisions = await self.get_all_revisions()

        # Filter to only applied revisions and sort by creation timestamp
        applied_revisions = [r for r in all_revisions if r["is_applied"]]
        applied_revisions.sort(key=lambda x: x.get("created_at") or "")

        logger.debug(
            "Retrieved migration history",
            total_revisions=len(all_revisions),
            applied_revisions=len(applied_revisions),
        )

        return applied_revisions

    def _is_revision_applied(self, revision_id: str, current_revision: str) -> bool:
        """Check if a revision is applied by checking if it's in the upgrade path.

        Args:
            revision_id: The revision to check.
            current_revision: The current database revision.

        Returns:
            True if the revision is applied, False otherwise.
        """
        if revision_id == current_revision:
            return True

        try:
            # Walk from current revision down to base
            current_rev_obj = self.script_dir.get_revision(current_revision)
            if not current_rev_obj:
                return False

            # Iterate through all down revisions
            for rev in self.script_dir.iterate_revisions(
                current_revision, "base", inclusive=True
            ):
                if rev.revision == revision_id:
                    return True

            return False
        except Exception as e:
            logger.warning(
                "Failed to check if revision is applied",
                revision=revision_id,
                error=str(e),
            )
            return False

    def _extract_creation_timestamp(self, revision) -> str | None:
        """Extract creation timestamp from revision.

        Args:
            revision: The revision object.

        Returns:
            ISO format timestamp string or None.
        """
        # Try to get timestamp from the revision's create_date attribute
        if hasattr(revision, "create_date") and revision.create_date:
            if isinstance(revision.create_date, datetime):
                return revision.create_date.isoformat()
            return str(revision.create_date)

        # Try to parse from the module docstring (format: "Create Date: YYYY-MM-DD HH:MM:SS")
        if revision.doc:
            lines = revision.doc.split("\n")
            for line in lines:
                if "Create Date:" in line:
                    try:
                        date_str = line.split("Create Date:")[-1].strip()
                        dt = datetime.fromisoformat(date_str)
                        return dt.isoformat()
                    except Exception:
                        pass

        # Try to get file modification time as fallback
        if revision.module and hasattr(revision.module, "__file__"):
            try:
                file_path = Path(revision.module.__file__)
                if file_path.exists():
                    mtime = file_path.stat().st_mtime
                    return datetime.fromtimestamp(mtime).isoformat()
            except Exception:
                pass

        return None
