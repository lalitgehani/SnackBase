"""Graceful self-restart after a restore request.

The API validates the archive, writes the marker, flushes the 202 response,
and only then terminates the process so the supervisor brings the instance
back — and the pre-boot executor performs the swap before the database is
ever opened. Exit code 75 (EX_TEMPFAIL) tells a supervised deployment that
the exit is an expected restart, not a crash.
"""

import asyncio
import atexit
import os
import signal

from snackbase.core.logging import get_logger

logger = get_logger(__name__)

#: ``EX_TEMPFAIL`` — conventionally "restart me" for supervised processes.
RESTORE_EXIT_CODE = 75

_shutdown_scheduled = False
_exit_code = 0


def _exit_with_code() -> None:
    os._exit(_exit_code)


def schedule_restart(exit_code: int = RESTORE_EXIT_CODE, delay_seconds: float = 1.0) -> None:
    """Send SIGTERM after ``delay_seconds`` so the response reaches the client.

    Uvicorn shuts the lifespan down gracefully on SIGTERM; the registered
    atexit hook then forces the agreed exit code so supervisors configured
    with ``Restart=on-failure``-style policies restart the instance.
    """
    global _shutdown_scheduled, _exit_code

    logger.info(
        "Restart scheduled for restore", exit_code=exit_code, delay=delay_seconds
    )
    _exit_code = exit_code
    if not _shutdown_scheduled:
        # Idempotent: the process is going down either way.
        atexit.register(_exit_with_code)
        _shutdown_scheduled = True

    async def _terminate() -> None:
        await asyncio.sleep(delay_seconds)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_terminate(), name="restore-restart")
