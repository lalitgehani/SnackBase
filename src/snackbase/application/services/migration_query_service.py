"""Migration query service for read-only Alembic migration information.

Provides programmatic access to Alembic migration status and history.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
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
        current_rev_ids = await self.get_current_revisions()

        # All branch heads (there may be two: core@head and dynamic@head)
        all_heads = set(self.script_dir.get_heads())

        # Get all revisions from the script directory
        for revision in self.script_dir.walk_revisions():
            # Determine if this is a dynamic migration
            module_path = revision.module.__file__ if revision.module else None
            is_dynamic = (
                any(path in module_path for path in ["dynamic", "sb_data/migrations"])
                if module_path
                else False
            )

            # Check if this revision is applied (against any of the current heads)
            is_applied = any(
                self._is_revision_applied(revision.revision, cur)
                for cur in current_rev_ids
            ) if current_rev_ids else False

            # A revision is a head if it is one of the branch heads
            is_head = revision.revision in all_heads

            # Extract creation timestamp from the revision module
            created_at = self._extract_creation_timestamp(revision)

            revisions.append(
                {
                    "revision": revision.revision,
                    "description": revision.doc or "",
                    "down_revision": revision.down_revision,
                    "branch_labels": list(revision.branch_labels) if revision.branch_labels else [],
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
            current=list(current_rev_ids),
        )

        return revisions

    async def get_current_revisions(self) -> list[str]:
        """Get all currently applied head revision IDs (one per branch).

        With the two-branch model (core + dynamic) there can be up to two
        simultaneously applied heads stored in the ``alembic_version`` table.

        Returns:
            List of currently applied revision IDs, empty if DB not initialised.
        """
        if not self.engine:
            logger.warning("No engine provided, cannot query current revisions")
            return []

        try:
            async with self.engine.connect() as connection:
                def get_revisions(sync_conn):
                    context = MigrationContext.configure(sync_conn)
                    # get_current_heads() returns all rows in alembic_version
                    return list(context.get_current_heads())

                rev_ids = await connection.run_sync(get_revisions)
                logger.debug("Retrieved current revisions", revisions=rev_ids)
                return rev_ids

        except Exception as e:
            logger.error("Failed to get current revisions", error=str(e))
            return []

    async def get_current_revision(self) -> dict[str, Any] | None:
        """Get the current database revision.

        For backwards compatibility this returns the most recently created
        applied head.  Prefer ``get_current_revisions()`` when you need all
        active heads (e.g. with core + dynamic branches).

        Returns:
            Current revision details or None if database is not initialized.
        """
        rev_ids = await self.get_current_revisions()
        if not rev_ids:
            logger.debug("No current revision found (database not initialized)")
            return None

        # Return the head with the most recent creation timestamp
        candidates = []
        for rev_id in rev_ids:
            revision_obj = self.script_dir.get_revision(rev_id)
            if not revision_obj:
                logger.warning(
                    "Current revision not found in script directory",
                    revision=rev_id,
                )
                candidates.append({"revision": rev_id, "description": "", "created_at": None})
                continue
            created_at = self._extract_creation_timestamp(revision_obj)
            candidates.append({
                "revision": revision_obj.revision,
                "description": revision_obj.doc or "",
                "created_at": created_at,
            })

        # Sort so the most recent comes first and return it
        candidates.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        result = candidates[0]
        logger.debug("Retrieved current revision", revision=result["revision"])
        return result

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

        Walks from ``current_revision`` back to base via ``down_revision`` links.
        Also follows ``depends_on`` edges so that core revisions reachable through
        a dynamic migration's ``depends_on`` are correctly identified as applied.

        Args:
            revision_id: The revision to check.
            current_revision: One of the currently applied head revisions.

        Returns:
            True if the revision is applied, False otherwise.
        """
        if revision_id == current_revision:
            return True

        try:
            visited: set[str] = set()
            queue = [current_revision]

            while queue:
                cur = queue.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                if cur == revision_id:
                    return True

                rev_obj = self.script_dir.get_revision(cur)
                if rev_obj is None:
                    continue

                # Follow down_revision (may be a tuple for merge revisions)
                down = rev_obj.down_revision
                if down:
                    if isinstance(down, (list, tuple)):
                        queue.extend(down)
                    else:
                        queue.append(down)

                # Follow depends_on (cross-branch ordering links)
                deps = rev_obj.dependencies
                if deps:
                    if isinstance(deps, (list, tuple)):
                        queue.extend(deps)
                    else:
                        queue.append(deps)

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
