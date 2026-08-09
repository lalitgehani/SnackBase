"""Online password-guessing defences for the login endpoint.

Two independent layers, because either alone leaves a usable attack:

* **Per-client-IP throttle** — in-memory, and charged *only* by failed attempts,
  so ordinary successful traffic never consumes the guessing budget. Stops one
  address from hammering many accounts.
* **Per-account lockout** — persisted on the user row, so it survives a restart
  and is shared by every instance pointed at the database. Stops a distributed
  attack from grinding one account.

The IP limit is deliberately tighter than the lockout threshold
(``login_rate_limit_per_minute`` < ``login_lockout_threshold``). An attacker who
hammers a single victim from one address therefore exhausts their own IP budget
long before the victim's account locks, which keeps the lockout from becoming a
denial-of-service primitive against arbitrary users.
"""

from datetime import UTC, datetime, timedelta

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.middleware.rate_limit_storage import rate_limit_storage
from snackbase.infrastructure.persistence.models import UserModel

logger = get_logger(__name__)

_KEY_PREFIX = "login-fail:"


def _key(client_ip: str) -> str:
    return f"{_KEY_PREFIX}{client_ip}"


def check_ip_throttle(client_ip: str) -> float | None:
    """Return seconds to wait if this address has spent its failure budget.

    Args:
        client_ip: The address the request is attributed to.

    Returns:
        Seconds until the next attempt is allowed, or None if it may proceed.
    """
    settings = get_settings()
    rate = settings.login_rate_limit_per_minute
    allowed, retry_after = rate_limit_storage.peek(_key(client_ip), rate, burst=rate)
    return None if allowed else retry_after


def record_ip_failure(client_ip: str) -> None:
    """Charge one failed attempt against the address's budget."""
    settings = get_settings()
    rate = settings.login_rate_limit_per_minute
    rate_limit_storage.consume(_key(client_ip), rate, burst=rate)


def clear_ip_failures(client_ip: str) -> None:
    """Forget an address's failures after a successful login from it."""
    rate_limit_storage.forget(_key(client_ip))


def account_lock_remaining(user: UserModel) -> float | None:
    """Return seconds remaining on this account's lockout, or None if unlocked."""
    if user.locked_until is None:
        return None

    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        # SQLite hands back naive datetimes even for timezone-aware columns.
        locked_until = locked_until.replace(tzinfo=UTC)

    remaining = (locked_until - datetime.now(UTC)).total_seconds()
    return remaining if remaining > 0 else None


def register_failure(user: UserModel) -> None:
    """Count a failed attempt against the account and lock it once over threshold.

    Each further lockout doubles the previous duration, so a persistent attacker
    faces a rapidly growing wait while a user who simply mistyped is delayed once.
    """
    settings = get_settings()
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

    if user.failed_login_attempts < settings.login_lockout_threshold:
        return

    lockouts_so_far = user.failed_login_attempts // settings.login_lockout_threshold
    duration = settings.login_lockout_seconds * (2 ** (lockouts_so_far - 1))
    user.locked_until = datetime.now(UTC) + timedelta(seconds=duration)

    logger.warning(
        "Account locked after repeated failed logins",
        account_id=user.account_id,
        user_id=user.id,
        failed_attempts=user.failed_login_attempts,
        lockout_seconds=duration,
    )


def register_success(user: UserModel) -> None:
    """Clear the failure counter and any lockout after a successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
