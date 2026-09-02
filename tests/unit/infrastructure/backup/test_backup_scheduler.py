"""Unit tests for the backup scheduler, retention, and alerting (F4.1-F4.3)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from snackbase.core.cron.parser import get_next_run
from snackbase.infrastructure.backup.alerting import BackupAlertManager
from snackbase.infrastructure.backup.retention import (
    AUTOMATIC_PREFIX,
    select_for_pruning,
)
from snackbase.infrastructure.backup.scheduler import (
    BackupScheduler,
    automatic_backup_name,
)
from snackbase.infrastructure.backup.service import create_backup


class TestAutomaticNames:
    def test_name_format_and_prefix(self) -> None:
        moment = datetime(2026, 9, 2, 2, 0, 0, tzinfo=UTC)
        name = automatic_backup_name(moment)
        assert name == "@auto_snackbase_20260902020000.zip"

    def test_names_use_utc(self) -> None:
        name = automatic_backup_name(datetime(2026, 9, 2, 2, 0, 0, tzinfo=UTC))
        assert name.endswith("020000.zip")


class TestSelectForPruning:
    def test_selects_oldest_beyond_max_keep(self) -> None:
        names = ["@auto_5.zip", "@auto_4.zip", "@auto_3.zip", "@auto_2.zip", "@auto_1.zip"]

        selected = select_for_pruning(names, max_keep=3)

        assert selected == ["@auto_2.zip", "@auto_1.zip"]

    def test_never_selects_the_archive_just_created(self) -> None:
        names = ["@auto_6.zip", "@auto_5.zip", "@auto_4.zip", "@auto_3.zip"]

        selected = select_for_pruning(
            names, max_keep=3, keep_name="@auto_6.zip"
        )

        assert "@auto_6.zip" not in selected
        # The new archive is protected even when max_keep is somehow zero.
        selected_zero = select_for_pruning(names, max_keep=0, keep_name="@auto_6.zip")
        assert "@auto_6.zip" not in selected_zero

    def test_no_pruning_when_under_limit(self) -> None:
        names = ["@auto_3.zip", "@auto_2.zip", "@auto_1.zip"]

        assert select_for_pruning(names, max_keep=3) == []

    def test_manual_archives_never_selected(self) -> None:
        names = ["manual.zip", "@auto_2.zip", "@auto_1.zip"]

        selected = select_for_pruning(names, max_keep=1)

        assert "manual.zip" not in selected


class _StubDestination:
    """In-memory destination shaped like BackupDestination for pruning tests."""

    def __init__(self, names: list[str]) -> None:
        self.names = list(names)
        self.deleted: list[str] = []

    async def list(self, prefix: str = ""):
        from datetime import datetime

        matching = sorted(
            (n for n in self.names if n.startswith(prefix)), reverse=True
        )
        return [
            type("E", (), {"name": n, "size": 1, "modified": datetime(2026, 9, 2)})()
            for n in matching
        ]

    async def delete(self, name: str) -> None:
        self.deleted.append(name)
        self.names.remove(name)


class TestPruneAutomaticBackups:
    async def test_prunes_to_max_keep(self) -> None:
        from snackbase.infrastructure.backup.retention import prune_automatic_backups

        destination = _StubDestination(
            [
                "@auto_new.zip",
                "@auto_5.zip",
                "@auto_4.zip",
                "@auto_3.zip",
                "@auto_2.zip",
                "@auto_1.zip",
            ]
        )

        deleted = await prune_automatic_backups(
            destination, max_keep=3, keep_name="@auto_new.zip"
        )

        assert destination.names == ["@auto_new.zip", "@auto_5.zip", "@auto_4.zip"]
        assert "@auto_new.zip" not in deleted

    async def test_deletion_failure_does_not_raise(self) -> None:
        from snackbase.infrastructure.backup.retention import prune_automatic_backups

        class FailingDestination(_StubDestination):
            async def delete(self, name: str) -> None:
                if name == "@auto_2.zip":
                    raise RuntimeError("s3 blip")
                await super().delete(name)

        destination = FailingDestination(
            ["@auto_3.zip", "@auto_2.zip", "@auto_1.zip"]
        )

        deleted = await prune_automatic_backups(destination, max_keep=1)

        # @auto_3.zip is the newest and is kept; the delete of @auto_2.zip
        # failed and was left in place.
        assert deleted == ["@auto_1.zip"]
        assert "@auto_2.zip" in destination.names
        assert "@auto_3.zip" in destination.names


class TestBackupScheduler:
    def _scheduler(self, cron_max: tuple[str, int], tmp_path: Path) -> BackupScheduler:
        class StubScheduler(BackupScheduler):
            def __init__(self) -> None:
                super().__init__(session_factory=None, settings=None)
                self.cron_max = cron_max
                self.ran: list[str] = []

            async def _read_backup_settings(self) -> tuple[str, int]:
                return self.cron_max

            async def _run_scheduled_backup(self, max_keep: int) -> None:
                self.ran.append((self._cron, max_keep))

        return StubScheduler()

    async def test_next_run_at_strictly_in_future_on_first_tick(self, tmp_path: Path) -> None:
        scheduler = self._scheduler(("0 2 * * *", 3), tmp_path)

        ran = await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, tzinfo=UTC))

        assert ran is False
        assert scheduler.next_run_at is not None
        assert scheduler.next_run_at > datetime(2026, 9, 2, 1, 0, tzinfo=UTC)

    async def test_fires_when_due(self, tmp_path: Path) -> None:
        scheduler = self._scheduler(("* * * * *", 3), tmp_path)

        # First tick schedules forward; the next tick after the window fires.
        await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, 30, tzinfo=UTC))
        ran = await scheduler._tick(now=datetime(2026, 9, 2, 1, 1, 5, tzinfo=UTC))

        assert ran is True
        assert scheduler.ran == [("* * * * *", 3)]

    async def test_changing_cron_recomputes_next_run(self, tmp_path: Path) -> None:
        scheduler = self._scheduler(("0 2 * * *", 3), tmp_path)
        await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, tzinfo=UTC))
        first_run = scheduler.next_run_at

        scheduler.cron_max = ("0 3 * * *", 3)
        await scheduler._tick(now=datetime(2026, 9, 2, 1, 30, tzinfo=UTC))

        assert scheduler.next_run_at != first_run
        expected = get_next_run("0 3 * * *", datetime(2026, 9, 2, 1, 30, tzinfo=UTC))
        assert scheduler.next_run_at == expected

    async def test_empty_cron_disables_schedule(self, tmp_path: Path) -> None:
        scheduler = self._scheduler(("", 3), tmp_path)

        ran = await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, tzinfo=UTC))

        assert ran is False
        assert scheduler.next_run_at is None

    async def test_invalid_cron_skipped_without_stopping(self, tmp_path: Path) -> None:
        scheduler = self._scheduler(("not a cron", 3), tmp_path)

        ran = await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, tzinfo=UTC))
        second = await scheduler._tick(now=datetime(2026, 9, 2, 1, 1, tzinfo=UTC))

        assert ran is False
        assert second is False
        assert scheduler.next_run_at is None

    async def test_loop_survives_tick_errors(self, tmp_path: Path, monkeypatch) -> None:
        scheduler = BackupScheduler(session_factory=None, settings=None, interval_seconds=0.01)
        calls = {"tick": 0}

        async def flaky_tick() -> bool:
            calls["tick"] += 1
            if calls["tick"] == 1:
                raise RuntimeError("boom")
            await scheduler.stop()
            return False

        monkeypatch.setattr(scheduler, "_tick", flaky_tick)
        scheduler._running = True
        await scheduler._loop()

        assert calls["tick"] >= 2

    async def test_in_progress_backup_skips_tick(self, tmp_path: Path) -> None:
        from snackbase.infrastructure.backup.lock import backup_lock

        scheduler = self._scheduler(("* * * * *", 3), tmp_path)
        working_dir = tmp_path / "backups"

        async with backup_lock("busy.zip", "backup", working_dir):
            ran = await scheduler._tick(now=datetime(2026, 9, 2, 1, 0, tzinfo=UTC))

        assert ran is False


class TestScheduledBackupEndToEnd:
    async def test_scheduled_run_creates_auto_archive_and_prunes(
        self, tmp_path: Path, db_session
    ) -> None:
        """A due tick creates an @auto_ archive and prunes to max_keep."""
        import uuid

        from snackbase.core.config import Settings
        from snackbase.infrastructure.backup.destinations import (
            LocalBackupDestination,
        )
        from snackbase.infrastructure.persistence.models.configuration import (
            ConfigurationModel,
        )

        # Configure backup settings: cron every minute, keep 3.
        db_session.add(
            ConfigurationModel(
                id=str(uuid.uuid4()),
                account_id="00000000-0000-0000-0000-000000000000",
                category="backup_settings",
                provider_name="backup",
                display_name="Backup Settings",
                config={"cron": "* * * * *", "max_keep": 3},
                enabled=True,
                is_builtin=True,
                is_system=True,
            )
        )
        await db_session.commit()

        live_db = tmp_path / "live.db"
        connection = __import__("sqlite3").connect(str(live_db))
        connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()

        settings = Settings(
            database_url=f"sqlite+aiosqlite:///{live_db}",
            storage_path=str(tmp_path / "files"),
            _env_file=None,
        )
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir(parents=True)
        destination = LocalBackupDestination(backups_dir)
        # Five pre-existing automatic archives; only @auto_-prefixed files.
        for suffix in ("a", "b", "c", "d", "e"):
            (backups_dir / f"@auto_snackbase_2026090100000{suffix}.zip").write_bytes(
                b"old"
            )
        (backups_dir / "manual_backup.zip").write_bytes(b"manual")

        class ResolvingScheduler(BackupScheduler):
            async def _read_backup_settings(self) -> tuple[str, int]:
                return await super()._read_backup_settings()

            async def _run_scheduled_backup(self, max_keep: int) -> None:
                await create_backup(
                    name=automatic_backup_name(),
                    destination=destination,
                    session_factory=_SessionFactory(db_session),
                    settings=settings,
                )
                from snackbase.infrastructure.backup.retention import (
                    prune_automatic_backups,
                )

                await prune_automatic_backups(
                    destination,
                    max_keep=max_keep,
                    keep_name=automatic_backup_name(datetime.now(UTC)),
                )

        scheduler = ResolvingScheduler(session_factory=_SessionFactory(db_session), settings=settings)
        first = datetime.now(UTC)
        await scheduler._tick(now=first)
        # Second tick, after the minute window: fires the backup.
        ran = await scheduler._tick(now=first + timedelta(seconds=61))

        assert ran is True
        remaining = sorted(p.name for p in backups_dir.glob("*.zip"))
        automatic = [n for n in remaining if n.startswith(AUTOMATIC_PREFIX)]
        assert len(automatic) == 3
        assert any(n.startswith("@auto_snackbase_2026") and n > "@auto_snackbase_20260901" for n in automatic)
        # Manual archive untouched.
        assert "manual_backup.zip" in remaining
        # jobs and hook_executions untouched by construction: the scheduler
        # never opens a session that writes to them; assert no job rows exist.
        from sqlalchemy import func, select

        from snackbase.infrastructure.persistence.models.job import JobModel

        count = await db_session.scalar(select(func.count()).select_from(JobModel))
        assert count == 0


class _SessionFactory:
    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self._session = session

    def __call__(self):  # type: ignore[no-untyped-def]
        return _NullContext(self._session)


class _NullContext:
    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self._session = session

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self._session

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class TestBackupAlertManager:
    def test_record_success_resets_failures(self) -> None:
        manager = BackupAlertManager()
        manager.record_failure("err")
        manager.record_failure("err")

        manager.record_success()

        assert manager.consecutive_failures == 0
        assert manager.last_error is None

    def test_suppression_sends_once_per_error_per_window(self) -> None:
        manager = BackupAlertManager()
        first = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)

        assert manager.should_send("boom", now=first) is True
        manager.mark_sent("boom", now=first)

        one_hour_later = first + timedelta(hours=1)
        assert manager.should_send("boom", now=one_hour_later) is False
        assert manager.consecutive_failures == 0  # record_failure not called here

    def test_different_errors_send_independently(self) -> None:
        manager = BackupAlertManager()
        first = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)
        manager.mark_sent("boom", now=first)

        assert manager.should_send("different", now=first + timedelta(hours=1)) is True

    def test_window_expiry_allows_repeat(self) -> None:
        manager = BackupAlertManager()
        first = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)
        manager.mark_sent("boom", now=first)

        assert manager.should_send("boom", now=first + timedelta(hours=25)) is True


class TestFailureAlertBody:
    def test_body_names_instance_archive_time_and_error(self) -> None:
        from snackbase.core.config import Settings
        from snackbase.infrastructure.backup.alerting import (
            ALERT_SUBJECT,
            failure_alert_body,
        )

        settings = Settings(_env_file=None, external_url="https://sb.example.com")
        body = failure_alert_body("@auto_x.zip", "s3 unreachable", settings)

        assert "https://sb.example.com" in body
        assert "@auto_x.zip" in body
        assert "s3 unreachable" in body
        assert ALERT_SUBJECT == "[SnackBase] Automatic backup failed"


class TestFailureAlertIntegration:
    async def test_alert_writes_email_log_per_superadmin(self, db_session) -> None:
        """A scheduled failure alerts each superadmin (email log row each)."""
        from sqlalchemy import func, select

        from snackbase.core.config import get_settings
        from snackbase.infrastructure.persistence.models.email_log import EmailLogModel
        from snackbase.infrastructure.persistence.models.role import RoleModel
        from snackbase.infrastructure.persistence.models.user import UserModel

        role = RoleModel(name="alert-admin", description="alert test role")
        db_session.add(role)
        await db_session.flush()
        for index, email in enumerate(
            ["super1@sb.test", "super2@sb.test"]
        ):
            db_session.add(
                UserModel(
                    id=f"alert-super-{index}",
                    email=email,
                    account_id="00000000-0000-0000-0000-000000000000",
                    password_hash="x",
                    role=role,
                    is_active=True,
                )
            )
        await db_session.commit()

        from snackbase.infrastructure.backup.alerting import BackupAlertManager

        manager = BackupAlertManager()
        sent = await manager.send_failure_alert(
            _SessionFactory(db_session),
            archive_name="@auto_x.zip",
            error="destination unreachable",
            settings=get_settings(),
        )

        # Without a configured email provider the send fails, but the email
        # log records one attempt per superadmin — that is the alert trail.
        assert sent is False
        assert manager.consecutive_failures == 1
        assert manager.last_error == "destination unreachable"
        count = await db_session.scalar(
            select(func.count()).select_from(EmailLogModel)
        )
        assert count == 2

    async def test_suppressed_alert_skips_email_log(self, db_session) -> None:
        from sqlalchemy import func, select

        from snackbase.core.config import get_settings
        from snackbase.infrastructure.backup.alerting import BackupAlertManager
        from snackbase.infrastructure.persistence.models.email_log import EmailLogModel

        manager = BackupAlertManager()
        now = datetime.now(UTC)
        manager.mark_sent("destination unreachable", now=now)

        sent = await manager.send_failure_alert(
            _SessionFactory(db_session),
            archive_name="@auto_x.zip",
            error="destination unreachable",
            settings=get_settings(),
            now=now + timedelta(minutes=5),
        )

        assert sent is False
        count = await db_session.scalar(
            select(func.count()).select_from(EmailLogModel)
        )
        assert count == 0
