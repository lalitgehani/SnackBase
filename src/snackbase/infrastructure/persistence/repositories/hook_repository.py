"""Repository for hook CRUD operations and scheduler queries."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.hook import HookModel


class HookRepository:
    """Database access layer for the hooks table.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, hook: HookModel) -> HookModel:
        """Persist a new hook record."""
        self._session.add(hook)
        await self._session.flush()
        return hook

    async def get(self, hook_id: str) -> HookModel | None:
        """Retrieve a hook by primary key."""
        result = await self._session.execute(
            select(HookModel).where(HookModel.id == hook_id)
        )
        return result.scalar_one_or_none()

    async def list_for_account(
        self,
        account_id: str,
        *,
        trigger_type: str | None = None,
        enabled: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[HookModel], int]:
        """List hooks for an account with optional filtering and pagination.

        Args:
            account_id: Tenant account ID.
            trigger_type: Filter by trigger type ("schedule" or "event").
            enabled: If not None, filter by enabled status.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            Tuple of (hooks, total_count).
        """
        base = select(HookModel).where(HookModel.account_id == account_id)

        if enabled is not None:
            base = base.where(HookModel.enabled == enabled)

        # Apply trigger_type filter in Python (JSON field, DB-agnostic)
        all_results = await self._session.execute(base.order_by(HookModel.created_at.desc()))
        all_hooks = list(all_results.scalars().all())

        if trigger_type is not None:
            all_hooks = [
                h for h in all_hooks
                if isinstance(h.trigger, dict) and h.trigger.get("type") == trigger_type
            ]

        total = len(all_hooks)
        return all_hooks[offset: offset + limit], total

    async def update(self, hook: HookModel) -> HookModel:
        """Persist changes to an existing hook."""
        await self._session.flush()
        return hook

    async def delete(self, hook_id: str) -> None:
        """Delete a hook by primary key."""
        hook = await self.get(hook_id)
        if hook:
            await self._session.delete(hook)
            await self._session.flush()

    # ------------------------------------------------------------------
    # Scheduler queries
    # ------------------------------------------------------------------

    async def get_due_scheduled_hooks(self, now: datetime) -> list[HookModel]:
        """Return enabled schedule-type hooks whose next_run_at has arrived.

        Fetches rows where ``enabled = True`` and ``next_run_at <= now``,
        then filters in Python for ``trigger.type == "schedule"``.
        The composite index on ``(enabled, next_run_at)`` keeps this efficient.

        Args:
            now: Current UTC datetime.

        Returns:
            List of HookModel instances ready to fire.
        """
        result = await self._session.execute(
            select(HookModel).where(
                HookModel.enabled == True,  # noqa: E712
                HookModel.next_run_at.is_not(None),
                HookModel.next_run_at <= now,
            )
        )
        hooks = list(result.scalars().all())
        return [
            h for h in hooks
            if isinstance(h.trigger, dict) and h.trigger.get("type") == "schedule"
        ]

    async def get_all_enabled_scheduled_hooks(self) -> list[HookModel]:
        """Return all enabled schedule-type hooks (used on startup for recalculation).

        Returns:
            List of all enabled schedule-type HookModel instances.
        """
        result = await self._session.execute(
            select(HookModel).where(HookModel.enabled == True)  # noqa: E712
        )
        hooks = list(result.scalars().all())
        return [
            h for h in hooks
            if isinstance(h.trigger, dict) and h.trigger.get("type") == "schedule"
        ]

    async def update_schedule_timestamps(
        self,
        hook_id: str,
        last_run_at: datetime | None,
        next_run_at: datetime,
    ) -> None:
        """Update scheduling timestamps after a hook fires.

        Args:
            hook_id: Hook primary key.
            last_run_at: Datetime the hook just fired (or None to leave unchanged).
            next_run_at: Next scheduled fire time.
        """
        values: dict = {"next_run_at": next_run_at}
        if last_run_at is not None:
            values["last_run_at"] = last_run_at

        await self._session.execute(
            update(HookModel)
            .where(HookModel.id == hook_id)
            .values(**values)
        )

    async def list_event_hooks_for_account(
        self,
        account_id: str,
        event_name: str,
        collection: str | None = None,
    ) -> list[HookModel]:
        """Return enabled event-type hooks matching the given event and collection.

        Filters are applied in Python to remain DB-agnostic over the JSON column.

        Args:
            account_id: Tenant account ID.
            event_name: Public event string (e.g. "records.create").
            collection: If provided, only return hooks targeting this collection
                        or hooks with no collection filter (None means any).

        Returns:
            List of matching HookModel instances.
        """
        result = await self._session.execute(
            select(HookModel).where(
                HookModel.account_id == account_id,
                HookModel.enabled == True,  # noqa: E712
            )
        )
        all_hooks = list(result.scalars().all())

        matching = []
        for hook in all_hooks:
            trigger = hook.trigger
            if not isinstance(trigger, dict):
                continue
            if trigger.get("type") != "event":
                continue
            if trigger.get("event") != event_name:
                continue
            hook_collection = trigger.get("collection")
            # hook_collection is None/missing means "fire for any collection"
            if hook_collection and collection and hook_collection != collection:
                continue
            matching.append(hook)

        return matching

    async def count_hooks_for_account(self, account_id: str) -> int:
        """Count all hooks (any trigger type) for an account.

        Used for limit enforcement (max 50 per account by default).

        Args:
            account_id: Tenant account ID.

        Returns:
            Total number of hooks for the account.
        """
        result = await self._session.execute(
            select(func.count(HookModel.id)).where(
                HookModel.account_id == account_id
            )
        )
        return result.scalar_one()

    async def count_scheduled_hooks_for_account(self, account_id: str) -> int:
        """Count schedule-type hooks for an account (for limit enforcement in F8.1).

        Args:
            account_id: Tenant account ID.

        Returns:
            Count of schedule-type hooks (enabled or disabled) for the account.
        """
        result = await self._session.execute(
            select(func.count(HookModel.id)).where(
                HookModel.account_id == account_id
            )
        )
        total = result.scalar_one()

        # Filter by trigger type in Python (JSON field)
        if total == 0:
            return 0

        all_result = await self._session.execute(
            select(HookModel.trigger).where(HookModel.account_id == account_id)
        )
        triggers = list(all_result.scalars().all())
        return sum(
            1 for t in triggers
            if isinstance(t, dict) and t.get("type") == "schedule"
        )
