"""Unit tests for MigrationQueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from snackbase.application.services.migration_query_service import MigrationQueryService


@pytest.fixture
def mock_script_directory():
    """Mock ScriptDirectory for testing."""
    mock_dir = MagicMock()
    
    # Create mock revisions
    mock_rev1 = MagicMock()
    mock_rev1.revision = "abc123"
    mock_rev1.doc = "Initial migration\n\nRevision ID: abc123\nRevises: \nCreate Date: 2025-01-01 10:00:00"
    mock_rev1.down_revision = None
    mock_rev1.branch_labels = {"core"}
    mock_rev1.dependencies = None
    mock_rev1.module = MagicMock()
    mock_rev1.module.__file__ = "/path/to/alembic/versions/abc123_initial.py"
    mock_rev1.create_date = "2025-01-01 10:00:00"

    mock_rev2 = MagicMock()
    mock_rev2.revision = "def456"
    mock_rev2.doc = "Add users table\n\nRevision ID: def456\nRevises: abc123\nCreate Date: 2025-01-02 10:00:00"
    mock_rev2.down_revision = "abc123"
    mock_rev2.branch_labels = None
    mock_rev2.dependencies = None
    mock_rev2.module = MagicMock()
    mock_rev2.module.__file__ = "/path/to/alembic/versions/def456_add_users.py"
    mock_rev2.create_date = "2025-01-02 10:00:00"

    mock_rev3 = MagicMock()
    mock_rev3.revision = "ghi789"
    mock_rev3.doc = "Create collection test\n\nRevision ID: ghi789\nRevises: def456\nCreate Date: 2025-01-03 10:00:00"
    mock_rev3.down_revision = None
    mock_rev3.branch_labels = {"dynamic"}
    mock_rev3.dependencies = ("def456",)
    mock_rev3.module = MagicMock()
    mock_rev3.module.__file__ = "/path/to/sb_data/migrations/ghi789_create_collection_test.py"
    mock_rev3.create_date = "2025-01-03 10:00:00"

    mock_dir.walk_revisions.return_value = [mock_rev3, mock_rev2, mock_rev1]
    mock_dir.get_heads.return_value = ["ghi789", "def456"]
    mock_dir.get_current_head.return_value = "def456"
    mock_dir.get_revision.side_effect = lambda rev: {
        "abc123": mock_rev1,
        "def456": mock_rev2,
        "ghi789": mock_rev3,
    }.get(rev)

    return mock_dir


@pytest.fixture
def migration_service(mock_script_directory):
    """Create a MigrationQueryService with mocked dependencies."""
    with patch("snackbase.application.services.migration_query_service.ScriptDirectory") as mock_sd:
        mock_sd.from_config.return_value = mock_script_directory
        service = MigrationQueryService(
            alembic_ini_path="alembic.ini",
            database_url="sqlite+aiosqlite:///test.db",
        )
        service.script_dir = mock_script_directory
        return service


@pytest.mark.asyncio
async def test_get_all_revisions_no_engine(migration_service, mock_script_directory):
    """Test get_all_revisions returns all revisions without engine."""
    # Service has no engine, so get_current_revisions returns []
    migration_service.engine = None

    revisions = await migration_service.get_all_revisions()

    assert len(revisions) == 3
    assert revisions[0]["revision"] == "ghi789"  # Newest first
    assert revisions[0]["is_head"] is True
    assert revisions[0]["is_dynamic"] is True
    assert revisions[1]["revision"] == "def456"
    assert revisions[1]["is_head"] is True   # also a head in the two-branch setup
    assert revisions[1]["is_dynamic"] is False
    assert revisions[2]["revision"] == "abc123"
    assert revisions[2]["is_dynamic"] is False


@pytest.mark.asyncio
async def test_get_all_revisions_with_current(migration_service, mock_script_directory):
    """Test get_all_revisions marks applied revisions correctly."""
    mock_engine = AsyncMock()
    migration_service.engine = mock_engine

    # Mock get_current_revisions: core at def456, dynamic at ghi789
    with patch.object(migration_service, "get_current_revisions", return_value=["def456", "ghi789"]):
        revisions = await migration_service.get_all_revisions()

        abc_rev = next(r for r in revisions if r["revision"] == "abc123")
        def_rev = next(r for r in revisions if r["revision"] == "def456")
        ghi_rev = next(r for r in revisions if r["revision"] == "ghi789")

        assert abc_rev["is_applied"] is True
        assert def_rev["is_applied"] is True
        assert ghi_rev["is_applied"] is True


@pytest.mark.asyncio
async def test_get_current_revision_no_engine(migration_service):
    """Test get_current_revision returns None when no engine provided."""
    migration_service.engine = None
    
    current = await migration_service.get_current_revision()
    
    assert current is None


@pytest.mark.asyncio
async def test_get_current_revision_with_engine(migration_service, mock_script_directory):
    """Test get_current_revision returns current revision from database."""
    from unittest.mock import AsyncMock, MagicMock

    mock_connection = MagicMock()

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_connection

        async def __aexit__(self, *args):
            return None

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=AsyncContextManager())

    # run_sync should return a list (get_current_heads returns list)
    async def mock_run_sync(func):
        mock_sync_conn = MagicMock()
        return func(mock_sync_conn)

    with patch("snackbase.application.services.migration_query_service.MigrationContext") as mock_mc:
        mock_context = MagicMock()
        mock_context.get_current_heads.return_value = ["def456"]
        mock_mc.configure.return_value = mock_context

        mock_connection.run_sync = mock_run_sync
        migration_service.engine = mock_engine

        current = await migration_service.get_current_revision()

        assert current is not None
        assert current["revision"] == "def456"
        assert current["description"].startswith("Add users table")


@pytest.mark.asyncio
async def test_get_current_revision_not_initialized(migration_service):
    """Test get_current_revision when database is not initialized."""
    # Create a mock engine with a proper async context manager for connect()
    from unittest.mock import MagicMock
    
    # Create the connection mock
    mock_connection = MagicMock()
    
    # Create an async context manager that returns the connection
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_connection
        
        async def __aexit__(self, *args):
            return None
    
    # Create the engine mock
    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=AsyncContextManager())
    
    # Mock run_sync to return None (no current revision)
    async def mock_run_sync(func):
        # Simulate calling the function with a sync connection
        mock_sync_conn = MagicMock()
        return func(mock_sync_conn)
    
    # Mock MigrationContext to return empty list (no revisions applied)
    with patch("snackbase.application.services.migration_query_service.MigrationContext") as mock_mc:
        mock_context = MagicMock()
        mock_context.get_current_heads.return_value = []
        mock_mc.configure.return_value = mock_context

        mock_connection.run_sync = mock_run_sync
        migration_service.engine = mock_engine

        current = await migration_service.get_current_revision()

        assert current is None


@pytest.mark.asyncio
async def test_get_migration_history(migration_service):
    """Test get_migration_history returns only applied migrations."""
    mock_engine = AsyncMock()
    migration_service.engine = mock_engine

    # Only core branch applied (def456 is core head; ghi789 dynamic not yet applied)
    with patch.object(migration_service, "get_current_revisions", return_value=["def456"]):
        history = await migration_service.get_migration_history()

        # Should only include abc123 and def456 (applied), not ghi789
        assert len(history) == 2
        # Should be in chronological order (oldest first)
        assert history[0]["revision"] == "abc123"
        assert history[1]["revision"] == "def456"


@pytest.mark.asyncio
async def test_get_migration_history_empty(migration_service):
    """Test get_migration_history when no migrations are applied."""
    migration_service.engine = None
    
    history = await migration_service.get_migration_history()
    
    # No engine means no applied migrations
    assert len(history) == 0


def test_is_revision_applied(migration_service):
    """Test _is_revision_applied correctly identifies applied revisions."""
    # Test revision that is current
    assert migration_service._is_revision_applied("def456", "def456") is True
    
    # Test revision in the upgrade path
    assert migration_service._is_revision_applied("abc123", "def456") is True
    
    # Test revision not in the upgrade path
    assert migration_service._is_revision_applied("ghi789", "def456") is False
