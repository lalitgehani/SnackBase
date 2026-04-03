"""Unit tests for F8.1 API-defined hook event dispatcher.

Tests cover:
- register_api_defined_hooks registers one callback per supported event
- Dispatcher skips when context has no account_id
- Condition evaluation: hook fires when condition matches
- Condition evaluation: hook skipped when condition does not match
- execute_hook_manually returns actions_executed and error
- _evaluate_condition falls back to True on parse errors
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.core.hooks.hook_events import HookEvent
from snackbase.core.hooks.hook_registry import HookRegistry
from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.hooks.api_defined_hook import (
    _evaluate_condition,
    register_api_defined_hooks,
)


# ---------------------------------------------------------------------------
# register_api_defined_hooks
# ---------------------------------------------------------------------------


def test_register_returns_one_id_per_event() -> None:
    """register_api_defined_hooks registers exactly one callback per supported event."""
    from snackbase.infrastructure.hooks.api_defined_hook import _EVENT_MAP

    registry = HookRegistry()
    hook_ids = register_api_defined_hooks(registry, session_factory=None)

    assert len(hook_ids) == len(_EVENT_MAP)
    assert all(hid is not None for hid in hook_ids)


def test_registered_hooks_are_not_builtin() -> None:
    """API-defined hook dispatchers are registered as non-builtin so they can be unregistered."""
    registry = HookRegistry()
    register_api_defined_hooks(registry, session_factory=None)

    # Get all hooks for a record event
    registered = registry.get_hooks_for_event(HookEvent.ON_RECORD_AFTER_CREATE)
    api_hooks = [h for h in registered if not h.is_builtin]
    # At minimum, our dispatcher should be there (may share with webhook_hook in full app)
    assert len(api_hooks) >= 1


# ---------------------------------------------------------------------------
# _evaluate_condition
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    def test_matching_condition_returns_true(self) -> None:
        result = _evaluate_condition('status = "published"', {"status": "published"})
        assert result is True

    def test_non_matching_condition_returns_false(self) -> None:
        result = _evaluate_condition('status = "published"', {"status": "draft"})
        assert result is False

    def test_parse_error_falls_back_to_true(self) -> None:
        """A bad condition string should not silently skip the hook."""
        result = _evaluate_condition("this is not a valid rule !!!###", {})
        assert result is True

    def test_empty_record_against_field_condition(self) -> None:
        """Missing field treated as None — condition with specific value should be False."""
        result = _evaluate_condition('status = "active"', {})
        assert result is False

    def test_in_operator(self) -> None:
        result = _evaluate_condition('status in ["draft", "published"]', {"status": "draft"})
        assert result is True

    def test_inequality_condition(self) -> None:
        result = _evaluate_condition('count != 0', {"count": 5})
        assert result is True


# ---------------------------------------------------------------------------
# execute_hook_manually
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_hook_manually_empty_actions() -> None:
    """execute_hook_manually with no actions returns (0, None) and logs execution."""
    from snackbase.infrastructure.hooks.api_defined_hook import execute_hook_manually

    hook = MagicMock()
    hook.id = "hook-123"
    hook.name = "Test Hook"
    hook.actions = []

    ctx = HookContext(app=None, account_id="acc-test")

    class FakeSession:
        async def flush(self):
            pass

        async def commit(self):
            pass

        async def get(self, model_class, pk):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    session_factory = lambda: FakeSession()  # noqa: E731

    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()

    # HookExecutionRepository is imported locally inside execute_hook_manually; patch at source
    with patch(
        "snackbase.infrastructure.persistence.repositories.hook_execution_repository.HookExecutionRepository",
        return_value=mock_repo,
    ):
        executed, error = await execute_hook_manually(
            hook=hook, context=ctx, session_factory=session_factory
        )

    assert executed == 0
    assert error is None
    mock_repo.create.assert_awaited_once()
    logged = mock_repo.create.call_args[0][0]
    assert logged.hook_id == "hook-123"
    assert logged.trigger_type == "manual"
    assert logged.status == "success"
    assert logged.actions_executed == 0


@pytest.mark.asyncio
async def test_execute_hook_manually_failed_action_sets_failed_status() -> None:
    """execute_hook_manually records status=failed when an action errors."""
    from snackbase.infrastructure.hooks.api_defined_hook import execute_hook_manually

    hook = MagicMock()
    hook.id = "hook-456"
    hook.name = "Failing Hook"
    hook.actions = [{"type": "send_webhook"}]  # missing URL — will error

    ctx = HookContext(app=None, account_id="acc-test")

    class FakeSession:
        async def flush(self):
            pass

        async def commit(self):
            pass

        async def get(self, *a):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()

    with patch(
        "snackbase.infrastructure.persistence.repositories.hook_execution_repository.HookExecutionRepository",
        return_value=mock_repo,
    ):
        executed, error = await execute_hook_manually(
            hook=hook, context=ctx, session_factory=lambda: FakeSession()
        )

    assert error is not None
    mock_repo.create.assert_awaited_once()
    logged = mock_repo.create.call_args[0][0]
    assert logged.status == "failed"
    assert logged.error_message is not None


# ---------------------------------------------------------------------------
# Dispatcher skips without account_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_skips_without_account_id() -> None:
    """_dispatch_api_hooks is a no-op when context has no account_id."""
    from snackbase.infrastructure.hooks.api_defined_hook import _dispatch_api_hooks

    # If it queries the DB without account_id it would blow up — so a mock that
    # raises if called proves we skip early.
    session_factory = MagicMock(side_effect=Exception("should not be called"))

    ctx_no_account = HookContext(app=None, account_id=None)

    # Should complete without error
    await _dispatch_api_hooks(
        internal_event=HookEvent.ON_RECORD_AFTER_CREATE,
        api_event="records.create",
        data={"record": {"id": "x"}, "collection": "posts"},
        context=ctx_no_account,
        session_factory=session_factory,
    )

    session_factory.assert_not_called()
