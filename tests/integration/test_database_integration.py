
import pytest
from snackbase.infrastructure.persistence.database import DatabaseManager, get_db_manager


@pytest.mark.asyncio
async def test_database_connection():
    """Test that the database manager can connect to the database."""
    # Create a fresh DatabaseManager instance to avoid event loop issues
    # when this test runs after other tests that may have closed the loop
    db = DatabaseManager()

    assert isinstance(db, DatabaseManager)

    try:
        # Check connection
        is_connected = await db.check_connection()
        assert is_connected is True
    finally:
        # Clean up the engine to prevent event loop issues in subsequent tests
        await db.disconnect()


@pytest.mark.asyncio
async def test_database_session_factory():
    """Test that the session factory creates valid sessions."""
    # Create a fresh DatabaseManager instance to avoid event loop issues
    db = DatabaseManager()

    try:
        async with db.session() as session:
            # Just check that we have a valid session context
            assert session is not None
            # Try a simple query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        # Clean up the engine to prevent event loop issues in subsequent tests
        await db.disconnect()
