"""Test-isolation helpers.

Guards the developer database so ``pytest`` from the repository root cannot
wipe ``sb_data/snackbase.db`` or ``sb_data/migrations``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DATA_DIR_ENV = "SNACKBASE_TEST_DATA_DIR"
DATABASE_URL_ENV = "SNACKBASE_DATABASE_URL"


def sqlite_path_from_url(database_url: str) -> Path | None:
    """Return the filesystem path of a SQLite SQLAlchemy URL, or ``None``."""
    if "sqlite" not in database_url:
        return None
    if ":///" not in database_url:
        return None
    raw = database_url.split(":///", 1)[1]
    raw = raw.split("?", 1)[0]
    if not raw:
        return None
    return Path(raw)


def assert_test_database_is_isolated(
    database_url: str,
    test_data_dir: str | Path,
) -> None:
    """Raise if ``database_url`` points at a ``snackbase.db`` outside the test dir.

    The error names the offending path and ``SNACKBASE_TEST_DATA_DIR``.
    """
    path = sqlite_path_from_url(database_url)
    if path is None:
        return
    if path.name != "snackbase.db":
        return

    resolved = path.resolve()
    test_root = Path(test_data_dir).resolve()
    try:
        resolved.relative_to(test_root)
    except ValueError as exc:
        raise RuntimeError(
            f"Refusing to run tests against {resolved} (named snackbase.db) "
            f"outside the test data directory {test_root}. Set "
            f"{TEST_DATA_DIR_ENV} to a dedicated directory."
        ) from exc


def configure_test_isolation() -> Path:
    """Set ``SNACKBASE_TEST_DATA_DIR`` and refuse a developer ``snackbase.db``.

    When ``SNACKBASE_DATABASE_URL`` is unset, point it at a file inside the
    test data directory so the default ``./sb_data/snackbase.db`` is never
    used. When it *is* set to a ``snackbase.db`` outside that directory, raise.
    """
    raw = os.environ.get(TEST_DATA_DIR_ENV)
    if raw:
        testdir = Path(raw)
    else:
        testdir = Path(tempfile.mkdtemp(prefix="snackbase_pytest_"))
        os.environ[TEST_DATA_DIR_ENV] = str(testdir)
    testdir.mkdir(parents=True, exist_ok=True)
    (testdir / "migrations").mkdir(parents=True, exist_ok=True)

    if DATABASE_URL_ENV not in os.environ:
        os.environ[DATABASE_URL_ENV] = f"sqlite+aiosqlite:///{testdir / 'test.db'}"

    assert_test_database_is_isolated(os.environ[DATABASE_URL_ENV], testdir)
    return testdir
