"""Unit tests for built-in hooks."""

import pytest

from snackbase.core.hooks import HookEvent, HookRegistry
from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.hooks import (
    account_isolation_hook,
    created_by_hook,
    register_builtin_hooks,
    timestamp_hook,
)


class MockUser:
    """Mock user for testing."""

    def __init__(self, user_id: str = "user_123"):
        self.id = user_id
        self.email = "test@example.com"


class TestTimestampHook:
    """Tests for the timestamp_hook."""

    @pytest.mark.asyncio
    async def test_sets_created_at_on_create(self) -> None:
        """Test that created_at is set on record creation."""
        data = {"title": "Test"}
        context = HookContext(app=None)

        result = await timestamp_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert "created_at" in result
        assert result["created_at"] is not None

    @pytest.mark.asyncio
    async def test_sets_updated_at_on_create(self) -> None:
        """Test that updated_at is set on record creation."""
        data = {"title": "Test"}
        context = HookContext(app=None)

        result = await timestamp_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert "updated_at" in result
        assert result["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_sets_updated_at_on_update(self) -> None:
        """Test that updated_at is set on record update."""
        data = {"title": "Updated"}
        context = HookContext(app=None)

        result = await timestamp_hook(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            data=data,
            context=context,
        )

        assert "updated_at" in result
        assert "created_at" not in result  # Should not add created_at on update

    @pytest.mark.asyncio
    async def test_handles_none_data(self) -> None:
        """Test that None data is handled gracefully."""
        context = HookContext(app=None)

        result = await timestamp_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=None,
            context=context,
        )

        assert result is None


class TestAccountIsolationHook:
    """Tests for the account_isolation_hook."""

    @pytest.mark.asyncio
    async def test_sets_account_id_on_create(self) -> None:
        """Test that account_id is set from context on creation."""
        data = {"title": "Test"}
        test_account_id = "550e8400-e29b-41d4-a716-446655440000"
        context = HookContext(app=None, account_id=test_account_id)

        result = await account_isolation_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert result["account_id"] == test_account_id

    @pytest.mark.asyncio
    async def test_does_not_set_without_context_account_id(self) -> None:
        """Test that account_id is not set if context has no account_id."""
        data = {"title": "Test"}
        context = HookContext(app=None, account_id=None)

        result = await account_isolation_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert "account_id" not in result

    @pytest.mark.asyncio
    async def test_handles_none_data(self) -> None:
        """Test that None data is handled gracefully."""
        context = HookContext(app=None, account_id="550e8400-e29b-41d4-a716-446655440000")

        result = await account_isolation_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=None,
            context=context,
        )

        assert result is None


class TestCreatedByHook:
    """Tests for the created_by_hook."""

    @pytest.mark.asyncio
    async def test_sets_created_by_on_create(self) -> None:
        """Test that created_by is set from user on creation."""
        data = {"title": "Test"}
        context = HookContext(app=None, user=MockUser("user_abc"))

        result = await created_by_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert result["created_by"] == "user_abc"

    @pytest.mark.asyncio
    async def test_sets_updated_by_on_create(self) -> None:
        """Test that updated_by is also set on creation."""
        data = {"title": "Test"}
        context = HookContext(app=None, user=MockUser("user_abc"))

        result = await created_by_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert result["updated_by"] == "user_abc"

    @pytest.mark.asyncio
    async def test_sets_updated_by_on_update(self) -> None:
        """Test that updated_by is set on update."""
        data = {"title": "Updated"}
        context = HookContext(app=None, user=MockUser("user_abc"))

        result = await created_by_hook(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            data=data,
            context=context,
        )

        assert result["updated_by"] == "user_abc"
        assert "created_by" not in result  # Should not add created_by on update

    @pytest.mark.asyncio
    async def test_handles_no_user(self) -> None:
        """Test that no user is handled gracefully."""
        data = {"title": "Test"}
        context = HookContext(app=None, user=None)

        result = await created_by_hook(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data=data,
            context=context,
        )

        assert "created_by" not in result


class TestRegisterBuiltinHooks:
    """Tests for the register_builtin_hooks function."""

    def test_registers_all_builtin_hooks(self) -> None:
        """Test that all built-in hooks are registered."""
        registry = HookRegistry()
        hook_ids = register_builtin_hooks(registry)

        # 2 timestamp + 1 account + 2 created_by + 3 audit capture
        assert len(hook_ids) == 8

    def test_builtin_hooks_cannot_be_unregistered(self) -> None:
        """Test that built-in hooks cannot be unregistered."""
        registry = HookRegistry()
        hook_ids = register_builtin_hooks(registry)

        for hook_id in hook_ids:
            result = registry.unregister(hook_id)
            assert result is False

    @pytest.mark.asyncio
    async def test_builtin_hooks_execute_on_create(self) -> None:
        """Test that built-in hooks execute on record creation."""
        registry = HookRegistry()
        register_builtin_hooks(registry)

        test_account_id = "550e8400-e29b-41d4-a716-446655440001"
        context = HookContext(
            app=None,
            user=MockUser("user_xyz"),
            account_id=test_account_id,
        )

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_CREATE,
            data={"title": "Test Post"},
            context=context,
        )

        assert result.success is True
        assert result.data["created_at"] is not None
        assert result.data["updated_at"] is not None
        assert result.data["account_id"] == test_account_id
        assert result.data["created_by"] == "user_xyz"
        assert result.data["updated_by"] == "user_xyz"

    @pytest.mark.asyncio
    async def test_builtin_hooks_execute_on_update(self) -> None:
        """Test that built-in hooks execute on record update."""
        registry = HookRegistry()
        register_builtin_hooks(registry)

        context = HookContext(
            app=None,
            user=MockUser("user_xyz"),
            account_id="550e8400-e29b-41d4-a716-446655440001",
        )

        result = await registry.trigger(
            event=HookEvent.ON_RECORD_BEFORE_UPDATE,
            data={"title": "Updated Post"},
            context=context,
        )

        assert result.success is True
        assert result.data["updated_at"] is not None
        assert result.data["updated_by"] == "user_xyz"
        # Should NOT set created_at or created_by on update
        assert "created_at" not in result.data
        assert "created_by" not in result.data
