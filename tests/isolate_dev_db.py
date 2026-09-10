"""Set test isolation env vars before any SnackBase import.

Imported first from ``tests/conftest.py`` so ``snackbase.core.config`` never
sees the developer ``sb_data/snackbase.db``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_DATA_DIR_ENV = "SNACKBASE_TEST_DATA_DIR"

if _TEST_DATA_DIR_ENV not in os.environ:
    os.environ[_TEST_DATA_DIR_ENV] = tempfile.mkdtemp(prefix="snackbase_pytest_")
Path(os.environ[_TEST_DATA_DIR_ENV], "migrations").mkdir(parents=True, exist_ok=True)
if "SNACKBASE_DATABASE_URL" not in os.environ:
    os.environ["SNACKBASE_DATABASE_URL"] = (
        f"sqlite+aiosqlite:///{Path(os.environ[_TEST_DATA_DIR_ENV]) / 'test.db'}"
    )
