"""Unit tests for the hook system infrastructure.

Tests cover:
- Hook registration and unregistration
- Priority ordering
- Tag-based filtering
- AbortHookException handling
- Error handling
- Built-in hooks
"""

import pytest

from snackbase.core.hooks import (
    HookCategory,
    HookDecorator,
    HookEvent,
    HookRegistry,
    get_all_events,
    is_after_event,
    is_before_event,
)
from snackbase.domain.entities.hook_context import (
    AbortHookException,
    HookContext,
    HookResult,
)


class TestHookRegistry:
    """Tests for the HookRegistry class."""

    def test_register_returns_unique_id(self) -> None:
        """Test that register() returns a unique hook ID."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_id = registry.register(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            callback=my_hook,
        )

        assert hook_id is not None
        assert hook_id.startswith("hook_")
        assert len(hook_id) > 5

    def test_register_creates_unique_ids(self) -> None:
        """Test that each registration gets a unique ID."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_ids = [
            registry.register(HookEvent.ON_RECORD_AFTER_CREATE, my_hook)
            for _ in range(10)
        ]

        # All IDs should be unique
        assert len(set(hook_ids)) == 10

    def test_register_with_filters(self) -> None:
        """Test that hooks can be registered with filters."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_id = registry.register(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            callback=my_hook,
            filters={"collection": "posts"},
        )

        hook = registry.get_hook_by_id(hook_id)
        assert hook is not None
        assert hook.filters == {"collection": "posts"}

    def test_register_with_priority(self) -> None:
        """Test that hooks can be registered with priority."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_id = registry.register(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            callback=my_hook,
            priority=10,
        )

        hook = registry.get_hook_by_id(hook_id)
        assert hook is not None
        assert hook.priority == 10

    def test_unregister_removes_hook(self) -> None:
        """Test that unregister() removes a hook."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_id = registry.register(HookEvent.ON_RECORD_AFTER_CREATE, my_hook)

        # Hook should exist
        assert registry.get_hook_by_id(hook_id) is not None

        # Unregister
        result = registry.unregister(hook_id)
        assert result is True

        # Hook should be gone
        assert registry.get_hook_by_id(hook_id) is None

    def test_unregister_returns_false_for_unknown_id(self) -> None:
        """Test that unregister() returns False for unknown IDs."""
        registry = HookRegistry()
        result = registry.unregister("hook_nonexistent")
        assert result is False

    def test_unregister_builtin_returns_false(self) -> None:
        """Test that built-in hooks cannot be unregistered."""
        registry = HookRegistry()

        async def my_hook(event, data, context):
            return data

        hook_id = registry.register(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            callback=my_hook,
            is_builtin=True,
        )

        result = registry.unregister(hook_id)
        assert result is False

        # Hook should still exist
        assert registry.get_hook_by_id(hook_id) is not None


class TestHookRegistryTrigger:
    """Tests for the HookRegistry.trigger() method."""

    @pytest.mark.asyncio
    async def test_trigger_executes_hooks(self) -> None:
        """Test that trigger() executes registered hooks."""
        registry = HookRegistry()
        executed = []

        async def my_hook(event, data, context):
            executed.append(event)
            return data

        registry.register(HookEvent.ON_RECORD_AFTER_CREATE, my_hook)

        await registry.trigger(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            data={"test": True},
        )

        assert len(executed) == 1
        assert executed[0] == HookEvent.ON_RECORD_AFTER_CREATE

    @pytest.mark.asyncio
    async def test_hooks_execute_in_priority_order(self) -> None:
        """Test that hooks execute in priority order (higher first)."""
        registry = HookRegistry()
        execution_order = []

        async def low_hook(event, data, context):
            execution_order.append("low")
            return data

        async def high_hook(event, data, context):
            execution_order.append("high")
            return data

        async def medium_hook(event, data, context):
            execution_order.append("medium")
            return data

        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, low_hook, priority=1)
        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, high_hook, priority=100)
        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, medium_hook, priority=50)

        await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={},
        )

        assert execution_order == ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_same_priority_executes_in_registration_order(self) -> None:
        """Test that same-priority hooks execute in registration order (FIFO)."""
        registry = HookRegistry()
        execution_order = []

        async def first_hook(event, data, context):
            execution_order.append("first")
            return data

        async def second_hook(event, data, context):
            execution_order.append("second")
            return data

        async def third_hook(event, data, context):
            execution_order.append("third")
            return data

        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, first_hook, priority=0)
        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, second_hook, priority=0)
        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, third_hook, priority=0)

        await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={},
        )

        assert execution_order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_hooks_can_modify_data(self) -> None:
        """Test that hooks can modify data."""
        registry = HookRegistry()

        async def add_field_hook(event, data, context):
            data["added_field"] = True
            return data

        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, add_field_hook)

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={"original": True},
        )

        assert result.data["original"] is True
        assert result.data["added_field"] is True


class TestHookRegistryFiltering:
    """Tests for tag-based filtering in hook trigger."""

    @pytest.mark.asyncio
    async def test_tag_filtering_only_calls_matching_hooks(self) -> None:
        """Test that only hooks matching the filter are called."""
        registry = HookRegistry()
        executed = []

        async def posts_hook(event, data, context):
            executed.append("posts")
            return data

        async def comments_hook(event, data, context):
            executed.append("comments")
            return data

        registry.register(
            HookEvent.ON_RECORD_AFTER_CREATE,
            posts_hook,
            filters={"collection": "posts"},
        )
        registry.register(
            HookEvent.ON_RECORD_AFTER_CREATE,
            comments_hook,
            filters={"collection": "comments"},
        )

        await registry.trigger(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            data={},
            filters={"collection": "posts"},
        )

        assert executed == ["posts"]

    @pytest.mark.asyncio
    async def test_hook_with_no_filter_matches_all(self) -> None:
        """Test that hooks with no filter match all triggers."""
        registry = HookRegistry()
        executed = []

        async def global_hook(event, data, context):
            executed.append("global")
            return data

        async def posts_hook(event, data, context):
            executed.append("posts")
            return data

        registry.register(HookEvent.ON_RECORD_AFTER_CREATE, global_hook)
        registry.register(
            HookEvent.ON_RECORD_AFTER_CREATE,
            posts_hook,
            filters={"collection": "posts"},
        )

        await registry.trigger(
            event=HookEvent.ON_RECORD_AFTER_CREATE,
            data={},
            filters={"collection": "posts"},
        )

        assert "global" in executed
        assert "posts" in executed


class TestHookRegistryErrorHandling:
    """Tests for error handling in hooks."""

    @pytest.mark.asyncio
    async def test_abort_hook_exception_cancels_operation(self) -> None:
        """Test that AbortHookException cancels the operation."""
        registry = HookRegistry()

        async def abort_hook(event, data, context):
            raise AbortHookException("Operation cancelled", 403)

        registry.register(HookEvent.ON_RECORD_BEFORE_CREATE, abort_hook)

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={},
        )

        assert result.success is False
        assert result.aborted is True
        assert result.abort_message == "Operation cancelled"
        assert result.abort_status_code == 403

    @pytest.mark.asyncio
    async def test_hook_error_logged_but_continues(self) -> None:
        """Test that hook errors are logged but don't stop execution."""
        registry = HookRegistry()
        executed = []

        async def error_hook(event, data, context):
            raise ValueError("Test error")

        async def success_hook(event, data, context):
            executed.append("success")
            return data

        registry.register(
            HookEvent.ON_RECORD_BEFORE_CREATE, error_hook, priority=10
        )
        registry.register(
            HookEvent.ON_RECORD_BEFORE_CREATE, success_hook, priority=5
        )

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={},
        )

        # Error was logged but execution continued
        assert len(result.errors) == 1
        assert "success" in executed
        assert result.success is True  # Overall success because stop_on_error=False

    @pytest.mark.asyncio
    async def test_stop_on_error_aborts_chain(self) -> None:
        """Test that stop_on_error=True stops the chain on error."""
        registry = HookRegistry()
        executed = []

        async def error_hook(event, data, context):
            raise ValueError("Test error")

        async def success_hook(event, data, context):
            executed.append("success")
            return data

        registry.register(
            HookEvent.ON_RECORD_BEFORE_CREATE,
            error_hook,
            priority=10,
            stop_on_error=True,
        )
        registry.register(
            HookEvent.ON_RECORD_BEFORE_CREATE, success_hook, priority=5
        )

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={},
        )

        assert result.success is False
        assert len(result.errors) == 1
        assert "success" not in executed  # Execution stopped before success_hook


class TestHookDecorator:
    """Tests for the HookDecorator class."""

    def test_decorator_syntax_registers_hook(self) -> None:
        """Test that decorator syntax registers a hook."""
        registry = HookRegistry()
        decorator = HookDecorator(registry)

        @decorator.on_record_after_create()
        async def my_hook(event, data, context):
            return data

        hooks = registry.get_hooks_for_event(HookEvent.ON_RECORD_AFTER_CREATE)
        assert len(hooks) == 1

    def test_collection_specific_decorator(self) -> None:
        """Test that collection parameter adds filter."""
        registry = HookRegistry()
        decorator = HookDecorator(registry)

        @decorator.on_record_after_create("posts")
        async def my_hook(event, data, context):
            return data

        hooks = registry.get_hooks_for_event(HookEvent.ON_RECORD_AFTER_CREATE)
        assert len(hooks) == 1
        assert hooks[0].filters == {"collection": "posts"}

    def test_decorator_with_priority(self) -> None:
        """Test that priority parameter is applied."""
        registry = HookRegistry()
        decorator = HookDecorator(registry)

        @decorator.on_record_after_create(priority=100)
        async def my_hook(event, data, context):
            return data

        hooks = registry.get_hooks_for_event(HookEvent.ON_RECORD_AFTER_CREATE)
        assert hooks[0].priority == 100


class TestHookEvents:
    """Tests for hook event definitions."""

    def test_get_all_events_returns_events(self) -> None:
        """Test that get_all_events() returns all defined events."""
        events = get_all_events()
        assert len(events) > 0
        assert HookEvent.ON_BOOTSTRAP in events
        assert HookEvent.ON_RECORD_AFTER_CREATE in events

    def test_is_before_event(self) -> None:
        """Test that is_before_event() correctly identifies before events."""
        assert is_before_event(HookEvent.ON_RECORD_BEFORE_CREATE) is True
        assert is_before_event(HookEvent.ON_RECORD_AFTER_CREATE) is False

    def test_is_after_event(self) -> None:
        """Test that is_after_event() correctly identifies after events."""
        assert is_after_event(HookEvent.ON_RECORD_AFTER_CREATE) is True
        assert is_after_event(HookEvent.ON_RECORD_BEFORE_CREATE) is False


class TestHookContext:
    """Tests for the HookContext dataclass."""

    def test_hook_context_creation(self) -> None:
        """Test that HookContext can be created with all fields."""
        test_account_id = "550e8400-e29b-41d4-a716-446655440000"
        context = HookContext(
            app=None,
            user=None,
            account_id=test_account_id,
            request_id="req_123",
        )

        assert context.app is None
        assert context.user is None
        assert context.account_id == test_account_id
        assert context.request_id == "req_123"

    def test_hook_context_generates_request_id(self) -> None:
        """Test that HookContext generates a request_id if not provided."""
        context = HookContext(app=None)

        assert context.request_id is not None
        assert context.request_id.startswith("hk_")


class TestAbortHookException:
    """Tests for the AbortHookException."""

    def test_abort_hook_exception_creation(self) -> None:
        """Test that AbortHookException can be created."""
        exc = AbortHookException("Test message", 403)

        assert exc.message == "Test message"
        assert exc.status_code == 403
        assert str(exc) == "Test message"

    def test_abort_hook_exception_default_status_code(self) -> None:
        """Test that AbortHookException defaults to 400."""
        exc = AbortHookException("Test message")

        assert exc.status_code == 400
