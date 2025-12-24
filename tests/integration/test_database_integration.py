
import pytest
from snackbase.infrastructure.persistence.database import get_db_manager, DatabaseManager


@pytest.mark.asyncio
async def test_database_connection():
    """Test that the database manager can connect to the database."""
    db = get_db_manager()
    
    assert isinstance(db, DatabaseManager)
    
    # Check connection
    is_connected = await db.check_connection()
    assert is_connected is True


@pytest.mark.asyncio
async def test_database_session_factory():
    """Test that the session factory creates valid sessions."""
    db = get_db_manager()
    
    async with db.session() as session:
        # Just check that we have a valid session context
        assert session is not None
        # Try a simple query
        from sqlalchemy import text
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
