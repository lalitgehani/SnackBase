"""Unit tests for the developer-database isolation guard."""

from pathlib import Path

import pytest

from snackbase.testing import (
    TEST_DATA_DIR_ENV,
    assert_test_database_is_isolated,
    sqlite_path_from_url,
)


def test_sqlite_path_from_relative_url():
    path = sqlite_path_from_url("sqlite+aiosqlite:///./sb_data/snackbase.db")
    assert path is not None
    assert path.name == "snackbase.db"


def test_guard_raises_for_developer_db_outside_test_dir(tmp_path: Path):
    testdir = tmp_path / "isolated"
    testdir.mkdir()
    url = f"sqlite+aiosqlite:///{tmp_path / 'sb_data' / 'snackbase.db'}"
    with pytest.raises(RuntimeError) as exc:
        assert_test_database_is_isolated(url, testdir)
    message = str(exc.value)
    assert "snackbase.db" in message
    assert TEST_DATA_DIR_ENV in message
    assert str((tmp_path / "sb_data" / "snackbase.db").resolve()) in message


def test_guard_passes_when_snackbase_db_is_inside_test_dir(tmp_path: Path):
    testdir = tmp_path / "isolated"
    testdir.mkdir()
    db = testdir / "snackbase.db"
    db.touch()
    assert_test_database_is_isolated(f"sqlite+aiosqlite:///{db}", testdir)


def test_guard_ignores_non_snackbase_filenames(tmp_path: Path):
    testdir = tmp_path / "isolated"
    testdir.mkdir()
    other = tmp_path / "test_db_1.sqlite"
    assert_test_database_is_isolated(f"sqlite+aiosqlite:///{other}", testdir)
