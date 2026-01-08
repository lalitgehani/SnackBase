import asyncio
import pytest
from unittest.mock import MagicMock, patch
from snackbase.infrastructure.persistence.event_listeners import _make_listener
from snackbase.core.hooks.hook_events import HookEvent

@pytest.mark.asyncio
async def test_background_task_error_handling():
    """Verify that background hook failures are caught and logged."""
    # 1. Setup mocks
    hook_registry = MagicMock()
    # Mock trigger to raise an exception
    hook_registry.trigger = MagicMock(side_effect=Exception("Test hook failure"))
    
    # Mock context
    context = MagicMock()
    
    # Mock target model
    target = MagicMock()
    target.__tablename__ = "test_table"
    
    # Mock mapper and connection
    mapper = MagicMock()
    mapper.primary_key = []
    connection = MagicMock()
    
    # Patch get_current_context to return our mock context
    with patch("snackbase.infrastructure.persistence.event_listeners.get_current_context", return_value=context), \
         patch("snackbase.infrastructure.persistence.event_listeners.ModelSnapshot", return_value=MagicMock()), \
         patch("snackbase.infrastructure.persistence.event_listeners.logger") as mock_logger:
        
        # 2. Create listener and trigger it
        listener = _make_listener(hook_registry, "insert")
        listener(mapper, connection, target)
        
        # 3. Wait for background task to complete
        # Since we use asyncio.create_task and _background_tasks.add, 
        # we need to wait a bit for it to run.
        from snackbase.infrastructure.persistence.event_listeners import _background_tasks
        
        # Give the loop a chance to run the task
        await asyncio.sleep(0.1)
        
        # 4. Verify
        # Check if error was logged
        assert mock_logger.error.called
        args, kwargs = mock_logger.error.call_args
        assert "Background hook execution failed" in args[0]
        assert "Test hook failure" == kwargs["error"]
        
        # Verify task was removed from _background_tasks
        assert len(_background_tasks) == 0

@pytest.mark.asyncio
async def test_background_task_tracking():
    """Verify that background tasks are tracked and then removed."""
    # 1. Setup mocks
    hook_registry = MagicMock()
    
    # Create a future to control when the hook finishes
    hook_done = asyncio.Future()
    
    async def mock_trigger(*args, **kwargs):
        await hook_done
    
    hook_registry.trigger = mock_trigger
    
    # Mock context
    context = MagicMock()
    
    # Mock target model
    target = MagicMock()
    target.__tablename__ = "test_table"
    
    # Mock mapper and connection
    mapper = MagicMock()
    mapper.primary_key = []
    connection = MagicMock()
    
    # Patch dependencies
    with patch("snackbase.infrastructure.persistence.event_listeners.get_current_context", return_value=context), \
         patch("snackbase.infrastructure.persistence.event_listeners.ModelSnapshot", return_value=MagicMock()):
        
        # 2. Create listener and trigger it
        listener = _make_listener(hook_registry, "insert")
        listener(mapper, connection, target)
        
        from snackbase.infrastructure.persistence.event_listeners import _background_tasks
        
        # 3. Verify task is in the set
        # Give the loop a tiny chance to start the task
        await asyncio.sleep(0.01)
        assert len(_background_tasks) == 1
        
        # 4. Complete the hook
        hook_done.set_result(None)
        
        # 5. Wait for task to finish
        await asyncio.sleep(0.1)
        
        # 6. Verify task is removed
        assert len(_background_tasks) == 0
