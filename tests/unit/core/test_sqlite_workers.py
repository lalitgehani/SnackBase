
import pytest
from pydantic import ValidationError
from snackbase.core.config import Settings

def test_valid_sqlite_workers():
    """Verify Settings accepts workers=1 with SQLite."""
    settings = Settings(
        database_url="sqlite+aiosqlite:///./test.db",
        workers=1
    )
    assert settings.workers == 1
    assert settings.database_url.startswith("sqlite")

def test_invalid_sqlite_workers():
    """Verify Settings raises ValueError for workers > 1 with SQLite."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="sqlite+aiosqlite:///./test.db",
            workers=2
        )
    assert "SQLite does not support multiple worker processes" in str(exc_info.value)

def test_valid_postgres_workers():
    """Verify Settings accepts workers > 1 with PostgreSQL."""
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        workers=4
    )
    assert settings.workers == 4
    assert settings.database_url.startswith("postgresql")
