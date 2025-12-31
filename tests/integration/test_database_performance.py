
import asyncio
import pytest
from sqlalchemy import text
from snackbase.infrastructure.persistence.database import get_db_manager
from snackbase.core.config import get_settings

@pytest.mark.asyncio
async def test_sqlite_pragmas():
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        pytest.skip("Not a SQLite database")
        
    db = get_db_manager()
    async with db.session() as session:
        # Check journal_mode
        result = await session.execute(text("PRAGMA journal_mode"))
        journal_mode = result.scalar()
        assert journal_mode.upper() == settings.db_sqlite_journal_mode.upper()
        
        # Check synchronous
        result = await session.execute(text("PRAGMA synchronous"))
        synchronous = result.scalar()
        # Mapping: 0=OFF, 1=NORMAL, 2=FULL, 3=EXTRA
        sync_map = {"OFF": 0, "NORMAL": 1, "FULL": 2, "EXTRA": 3}
        assert synchronous == sync_map.get(settings.db_sqlite_synchronous.upper())
        
        # Check cache_size
        result = await session.execute(text("PRAGMA cache_size"))
        cache_size = result.scalar()
        assert cache_size == settings.db_sqlite_cache_size
        
        # Check temp_store
        result = await session.execute(text("PRAGMA temp_store"))
        temp_store = result.scalar()
        # Mapping: 0=DEFAULT, 1=FILE, 2=MEMORY
        temp_map = {"DEFAULT": 0, "FILE": 1, "MEMORY": 2}
        assert temp_store == temp_map.get(settings.db_sqlite_temp_store.upper())

@pytest.mark.asyncio
async def test_connection_pool_settings():
    db = get_db_manager()
    settings = get_settings()
    engine = db.engine
    
    # Check pool size and max overflow
    # These are only available for engines that use a QueuePool (not NullPool used by default in some cases)
    # create_async_engine uses QueuePool by default for non-sqlite or if configured
    if hasattr(engine.pool, "_size"):
        assert engine.pool._size == settings.db_pool_size
    if hasattr(engine.pool, "_max_overflow"):
        assert engine.pool._max_overflow == settings.db_max_overflow
