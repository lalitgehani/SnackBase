"""Failure alerting for scheduled backups.

A backup nobody watches must announce its own failure: on a scheduled-run
failure every superadmin gets one email per distinct error per 24 hours, so
a destination misconfiguration that fails hourly does not send 24 identical
emails. Alerting problems are logged and never mask the backup error that
triggered them.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from snackbase.core.config import Settings, get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

ALERT_SUBJECT = "[SnackBase] Automatic backup failed"
SUPPRESSION_WINDOW = timedelta(hours=24)
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


class BackupAlertManager:
    """Tracks consecutive failures and suppresses duplicate alerts."""

    def __init__(self) -> None:
        self.consecutive_failures: int = 0
        self.last_error: str | None = None
        self._last_sent_at: dict[str, datetime] = {}

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.last_error = None

    def record_failure(self, error: str) -> None:
        self.consecutive_failures += 1
        self.last_error = error

    def should_send(self, error: str, now: datetime | None = None) -> bool:
        """At most one alert per 24 hours per distinct error message."""
        moment = now or datetime.now(UTC)
        last = self._last_sent_at.get(error)
        if last is not None and moment - last < SUPPRESSION_WINDOW:
            return False
        return True

    def mark_sent(self, error: str, now: datetime | None = None) -> None:
        self._last_sent_at[error] = now or datetime.now(UTC)

    async def send_failure_alert(
        self,
        session_factory: Any,
        *,
        archive_name: str,
        error: str,
        settings: Settings | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Email every superadmin about a failed scheduled backup.

        Returns whether an alert was sent. Never raises: an alerting
        failure is logged and does not change the backup's recorded
        outcome.
        """
        self.record_failure(error)
        settings = settings or get_settings()
        if not self.should_send(error, now=now):
            logger.info(
                "Backup failure alert suppressed (already sent for this error "
                "within 24 hours)",
                archive=archive_name,
            )
            return False
        try:
            sent = await _send_alert_emails(
                session_factory,
                settings=settings,
                archive_name=archive_name,
                error=error,
            )
        except Exception as exc:  # noqa: BLE001 - alerting must not mask backup
            logger.error(
                "Failed to send backup failure alert",
                archive=archive_name,
                error=str(exc),
            )
            return False
        if sent:
            self.mark_sent(error, now=now)
        return sent


def failure_alert_body(archive_name: str, error: str, settings: Settings) -> str:
    """Human-readable alert body naming instance, archive, time, and error."""
    moment = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    instance = settings.external_url or "http://localhost:8000"
    return (
        f"The automatic backup of {instance} failed.\n\n"
        f"Archive: {archive_name}\n"
        f"Time: {moment}\n"
        f"Error: {error}\n\n"
        "Check the backup settings and destination, and inspect "
        "GET /api/v1/backups for the recorded failure."
    )


async def _send_alert_emails(
    session_factory: Any,
    *,
    settings: Settings,
    archive_name: str,
    error: str,
) -> bool:
    """Deliver the alert to each superadmin; True when at least one sent."""
    from snackbase.infrastructure.persistence.models.user import UserModel
    from snackbase.infrastructure.persistence.repositories.configuration_repository import (
        ConfigurationRepository,
    )
    from snackbase.infrastructure.persistence.repositories.email_log_repository import (
        EmailLogRepository,
    )
    from snackbase.infrastructure.persistence.repositories.email_template_repository import (
        EmailTemplateRepository,
    )
    from snackbase.infrastructure.security.encryption import EncryptionService
    from snackbase.infrastructure.services.email_service import EmailService

    body = failure_alert_body(archive_name, error, settings)
    sent_any = False
    async with session_factory() as session:
        result = await session.execute(
            select(UserModel.email).where(
                UserModel.account_id == SYSTEM_ACCOUNT_ID,
                UserModel.is_active == True,  # noqa: E712
            )
        )
        recipients = [row[0] for row in result.fetchall()]

        if not recipients:
            logger.warning(
                "No active superadmin found for backup failure alert",
                archive=archive_name,
            )
            return False

        email_service = EmailService(
            EmailTemplateRepository(),
            EmailLogRepository(),
            ConfigurationRepository(session),
            EncryptionService(settings.encryption_key),
        )
        for recipient in recipients:
            try:
                ok = await email_service.send_email(
                    session,
                    to=recipient,
                    subject=ALERT_SUBJECT,
                    html_body=f"<pre>{body}</pre>",
                    text_body=body,
                    account_id=SYSTEM_ACCOUNT_ID,
                    template_type="custom",
                )
                sent_any = sent_any or ok
            except Exception as exc:  # noqa: BLE001 - per-recipient isolation
                logger.error(
                    "Failed to email backup alert to superadmin",
                    recipient=recipient,
                    error=str(exc),
                )
        await session.commit()
    return sent_any
