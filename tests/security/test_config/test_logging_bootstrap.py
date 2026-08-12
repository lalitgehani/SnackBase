"""CFG-LOG-*: production logging bootstrap (M-10).

The production branch of ``configure_logging`` calls::

    logging.basicConfig(format=..., stream=sys.stdout, level=..., handlers=[...])

``basicConfig`` rejects ``stream`` and ``handlers`` together. The check only
runs when the root logger has no handlers yet — which is exactly the state at
process start, so it fires on a real production boot and not in a test process
that has already installed handlers.

The default configuration is ``environment="production"`` plus
``log_format="json"``. This is not an exotic combination; it is the shipping
default, and it raises before the app can serve a request.

Every test here clears the root handlers first so the assertions describe the
real boot path rather than the incidental state of the test runner.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import structlog

from snackbase.core.config import Settings
from snackbase.core.logging import configure_logging

VALID_SECRETS = {
    "secret_key": "a-real-secret-key-for-tests-32byte",
    "token_secret": "a-real-token-secret-for-tests-32b",
    "encryption_key": "production-encryption-key-value-32",
}


@contextmanager
def pristine_root_logger() -> Iterator[None]:
    """Run the block with a handler-free root logger, as at process start.

    Used inside the test body rather than as a fixture: pytest reinstalls its
    own capture handler on the root logger between setup and call, which would
    hide the very `basicConfig` branch under test.
    """
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_structlog = structlog.get_config()
    root.handlers = []
    try:
        yield
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
        structlog.configure(**saved_structlog)


def test_cfg_log_001_production_json_logging_configures_cleanly() -> None:
    """CFG-LOG-001: the shipping default must not raise during bootstrap."""
    settings = Settings(environment="production", log_format="json", **VALID_SECRETS)

    with pristine_root_logger():
        configure_logging(settings)


def test_cfg_log_002_app_factory_starts_under_production_json_logging() -> None:
    """CFG-LOG-002: the app must be constructible under the same settings."""
    from snackbase.infrastructure.api.app import create_app

    settings = Settings(environment="production", log_format="json", **VALID_SECRETS)

    with pristine_root_logger():
        configure_logging(settings)
        assert create_app() is not None


@pytest.mark.parametrize(
    ("environment", "log_format"),
    [
        ("development", "console"),
        ("development", "json"),
        ("testing", "console"),
    ],
)
def test_cfg_log_003_other_combinations_configure_cleanly(
    environment: str, log_format: str
) -> None:
    """CFG-LOG-003: regression — the console path is unaffected.

    `development` takes the console branch regardless of `log_format`, so all
    three of these avoid the broken `basicConfig` call today.
    """
    settings = Settings(environment=environment, log_format=log_format)

    with pristine_root_logger():
        configure_logging(settings)
