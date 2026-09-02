"""Dedicated scheduler for automatic backups.

Backups deliberately do not ride the hook scheduler or the ``jobs`` table: a
backup job row recorded in the database it is snapshotting would come back
from every restore as a job stuck in ``running``. This scheduler holds its
next-run time in memory and re-reads its cron expression from configuration
each tick, so settings changes take effect without a restart. Its only
persistent traces are the archives themselves and the audit entries the
backup service already writes.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from snackbase.core.config import Settings, get_settings
from snackbase.core.cron.parser import get_next_run
from snackbase.core.logging import get_logger
from snackbase.infrastructure.backup.destinations import (
    BackupInProgressError,
    resolve_destination,
)
from snackbase.infrastructure.backup.lock import active_operation
from snackbase.infrastructure.backup.retention import (
    AUTOMATIC_PREFIX,
    prune_automatic_backups,
)
from snackbase.infrastructure.backup.service import (
    backup_working_dir,
    create_backup,
)

logger = get_logger(__name__)


def automatic_backup_name(moment: datetime | None = None) -> str:
    """Reserved-prefix archive name: ``@auto_snackbase_<UTC yyyymmddHHMMSS>.zip``."""
    stamp = (moment or datetime.now(UTC)).strftime("%Y%m%d%H%M%S")
    return f"{AUTOMATIC_PREFIX}snackbase_{stamp}.zip"


class BackupScheduler:
    """Runs cron-scheduled backups without touching the jobs or hooks tables.

    Args:
        session_factory: Session factory used to read ``backup_settings``
            and to write audit entries through the backup service.
        settings: Application settings.
        interval_seconds: Tick interval; 60 seconds in production, lowered
            in tests.
    """

    def __init__(
        self,
        session_factory: Any,
        settings: Settings | None = None,
        interval_seconds: float = 60.0,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._interval = interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._cron: str | None = None
        self.next_run_at: datetime | None = None
        from snackbase.infrastructure.backup.alerting import BackupAlertManager

        self.alerts = BackupAlertManager()

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="snackbase-backup-scheduler")
        logger.info(
            "Backup scheduler started",
            interval_seconds=self._interval,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Backup scheduler stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - the loop must survive
                logger.error("Backup scheduler tick error", error=str(exc))
            await asyncio.sleep(self._interval)

    async def _tick(self, now: datetime | None = None) -> bool:
        """One scheduler tick: re-read config, fire when due.

        Returns whether a backup ran (exposed for tests).
        """
        moment = now or datetime.now(UTC)
        cron, max_keep = await self._read_backup_settings()

        if cron != self._cron:
            # Schedule change (or first tick): compute forward from now so a
            # restart never fires a missed window immediately.
            self._cron = cron
            self.next_run_at = self._compute_next_run(cron, moment)

        if self.next_run_at is None or moment < self.next_run_at:
            return False

        await self._run_scheduled_backup(max_keep)
        self.next_run_at = self._compute_next_run(cron, datetime.now(UTC))
        return True

    @staticmethod
    def _compute_next_run(cron: str, from_dt: datetime) -> datetime | None:
        if not cron:
            return None
        try:
            return get_next_run(cron, from_dt)
        except ValueError as exc:
            logger.warning(
                "Backup scheduler has an invalid cron expression; "
                "schedule disabled until it is fixed",
                cron=cron,
                error=str(exc),
            )
            return None

    async def _read_backup_settings(self) -> tuple[str, int]:
        """Re-read the schedule each tick, so changes apply without restart."""
        from snackbase.core.configuration.config_registry import ConfigurationRegistry
        from snackbase.infrastructure.configuration.providers.backup.backup_settings import (
            BackupSettingsConfiguration,
        )
        from snackbase.infrastructure.persistence.repositories.configuration_repository import (
            ConfigurationRepository,
        )
        from snackbase.infrastructure.security.encryption import EncryptionService

        settings = self._settings or get_settings()
        provider = BackupSettingsConfiguration()
        registry = ConfigurationRegistry(EncryptionService(settings.encryption_key))
        async with self._session_factory() as session:
            repository = ConfigurationRepository(session)
            config = await registry.get_effective_config(
                provider.category,
                ConfigurationRegistry.SYSTEM_ACCOUNT_ID,
                provider.provider_name,
                repository,
            )
        if not config:
            return "", 3
        cron = str(config.get("cron") or "")
        try:
            max_keep = max(1, int(config.get("max_keep", 3)))
        except (TypeError, ValueError):
            max_keep = 3
        return cron, max_keep

    async def _run_scheduled_backup(self, max_keep: int) -> None:
        name = automatic_backup_name()
        settings = self._settings or get_settings()
        try:
            session_factory = self._session_factory
            async with session_factory() as session:
                destination = await resolve_destination(session)
            working_dir = backup_working_dir(destination)

            if active_operation(working_dir) is not None:
                logger.info(
                    "Scheduled backup skipped: another operation is in flight",
                    archive=name,
                )
                return
            try:
                outcome = await create_backup(
                    name=name,
                    destination=destination,
                    session_factory=session_factory,
                    settings=settings,
                )
            except BackupInProgressError:
                logger.info(
                    "Scheduled backup skipped: lost the activation race",
                    archive=name,
                )
                return

            # Prune only after the new archive is confirmed written.
            await prune_automatic_backups(
                destination,
                max_keep=max_keep,
                keep_name=name,
                session_factory=session_factory,
            )
            self.alerts.record_success()
            logger.info(
                "Scheduled backup completed",
                archive=outcome.name,
                size=outcome.size,
            )
        except Exception as exc:  # noqa: BLE001 - failures alert, never crash
            logger.error(
                "Scheduled backup failed", archive=name, error=str(exc)
            )
            try:
                await self.alerts.send_failure_alert(
                    self._session_factory,
                    archive_name=name,
                    error=str(exc),
                    settings=settings,
                )
            except Exception as alert_exc:  # noqa: BLE001 - never masks backup error
                logger.error(
                    "Backup failure alerting itself failed", error=str(alert_exc)
                )
