"""Unit tests for F8.1 action executor.

Tests cover:
- Template variable resolution (record fields, auth context, now)
- Recursive resolution in nested dicts and lists
- Depth guard (cycle detection)
- send_webhook action
- enqueue_job action
- Unknown action type is skipped (not an error)
- First action failure aborts remaining actions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.hooks.action_executor import (
    _MAX_DEPTH,
    _resolve_template,
    _resolve_value,
    execute_actions,
)


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


class TestResolveTemplate:
    """Tests for _resolve_template()."""

    def _ctx(self) -> HookContext:
        from snackbase.domain.entities.user import User

        user = User(
            id="user-abc",
            account_id="acc-1",
            email="alice@example.com",
            password_hash="x",
            role_id=1,
        )
        return HookContext(app=None, user=user, account_id="acc-1")

    def test_record_field(self) -> None:
        record = {"title": "Hello World", "status": "published"}
        result = _resolve_template("Title is {{record.title}}", record, None)
        assert result == "Title is Hello World"

    def test_record_field_missing_returns_empty(self) -> None:
        result = _resolve_template("{{record.nonexistent}}", {}, None)
        assert result == ""

    def test_auth_user_id(self) -> None:
        ctx = self._ctx()
        result = _resolve_template("User: {{auth.user_id}}", {}, ctx)
        assert result == "User: user-abc"

    def test_auth_email(self) -> None:
        ctx = self._ctx()
        result = _resolve_template("Email: {{auth.email}}", {}, ctx)
        assert result == "Email: alice@example.com"

    def test_now_is_replaced(self) -> None:
        result = _resolve_template("Time: {{now}}", {}, None)
        assert "Time: " in result
        assert "{{now}}" not in result

    def test_unknown_variable_left_as_is(self) -> None:
        result = _resolve_template("{{unknown.var}}", {}, None)
        assert result == "{{unknown.var}}"

    def test_no_placeholders_unchanged(self) -> None:
        result = _resolve_template("no placeholders here", {"x": 1}, None)
        assert result == "no placeholders here"

    def test_multiple_placeholders(self) -> None:
        record = {"id": "rec-1", "status": "active"}
        ctx = self._ctx()
        result = _resolve_template(
            "Record {{record.id}} by {{auth.user_id}} is {{record.status}}", record, ctx
        )
        assert result == "Record rec-1 by user-abc is active"

    def test_auth_user_id_no_user_returns_empty(self) -> None:
        ctx = HookContext(app=None, account_id="acc-1")
        result = _resolve_template("{{auth.user_id}}", {}, ctx)
        assert result == ""


class TestResolveValue:
    """Tests for _resolve_value() — recursive resolution."""

    def test_string_is_resolved(self) -> None:
        result = _resolve_value("{{record.name}}", {"name": "Bob"}, None)
        assert result == "Bob"

    def test_dict_values_resolved(self) -> None:
        result = _resolve_value(
            {"url": "https://example.com/{{record.id}}", "method": "POST"},
            {"id": "42"},
            None,
        )
        assert result == {"url": "https://example.com/42", "method": "POST"}

    def test_list_items_resolved(self) -> None:
        result = _resolve_value(["{{record.a}}", "{{record.b}}"], {"a": "1", "b": "2"}, None)
        assert result == ["1", "2"]

    def test_nested_dict_and_list(self) -> None:
        data = {"headers": {"X-ID": "{{record.id}}"}, "tags": ["{{record.tag}}"]}
        result = _resolve_value(data, {"id": "abc", "tag": "vip"}, None)
        assert result == {"headers": {"X-ID": "abc"}, "tags": ["vip"]}

    def test_non_string_passthrough(self) -> None:
        assert _resolve_value(42, {}, None) == 42
        assert _resolve_value(True, {}, None) is True
        assert _resolve_value(None, {}, None) is None


# ---------------------------------------------------------------------------
# execute_actions — depth guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_depth_guard_prevents_execution() -> None:
    """Actions are not executed when depth >= _MAX_DEPTH."""
    actions = [{"type": "enqueue_job", "handler": "some_handler", "payload": {}}]
    executed, error = await execute_actions(
        actions=actions,
        record={},
        context=None,
        session_factory=None,
        depth=_MAX_DEPTH,
    )
    assert executed == 0
    assert error is not None
    assert "depth" in error.lower() or "cycle" in error.lower()


# ---------------------------------------------------------------------------
# execute_actions — send_webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_webhook_action_fires_http_request() -> None:
    """send_webhook action calls httpx with the resolved URL and method."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.request = AsyncMock(return_value=mock_response)

    # httpx is imported locally inside _execute_send_webhook, so patch at source
    with patch("httpx.AsyncClient", return_value=mock_client):
        actions = [
            {
                "type": "send_webhook",
                "url": "https://example.com/notify/{{record.id}}",
                "method": "POST",
            }
        ]
        executed, error = await execute_actions(
            actions=actions,
            record={"id": "rec-99"},
            context=None,
            session_factory=None,
        )

    assert executed == 1
    assert error is None
    mock_client.request.assert_awaited_once()
    call_args = mock_client.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "https://example.com/notify/rec-99"


@pytest.mark.asyncio
async def test_send_webhook_missing_url_returns_error() -> None:
    """send_webhook action without a URL records an error and stops execution."""
    actions = [{"type": "send_webhook"}]
    executed, error = await execute_actions(
        actions=actions, record={}, context=None, session_factory=None
    )
    assert executed == 0
    assert error is not None
    assert "url" in error.lower()


@pytest.mark.asyncio
async def test_send_webhook_http_error_aborts_chain() -> None:
    """HTTP 4xx/5xx from send_webhook stops action chain and returns error."""
    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
    )
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        actions = [
            {"type": "send_webhook", "url": "https://example.com/hook"},
            {"type": "send_webhook", "url": "https://example.com/second"},  # should not run
        ]
        executed, error = await execute_actions(
            actions=actions, record={}, context=None, session_factory=None
        )

    assert executed == 0
    assert error is not None


# ---------------------------------------------------------------------------
# execute_actions — enqueue_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_job_action_creates_job() -> None:
    """enqueue_job action creates a JobModel via the JobRepository."""

    class FakeSession:
        async def flush(self):
            pass

        async def commit(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    session_factory = lambda: FakeSession()  # noqa: E731

    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock(return_value=None)

    # JobRepository is imported locally inside _execute_enqueue_job; patch at source
    with patch(
        "snackbase.infrastructure.persistence.repositories.job_repository.JobRepository",
        return_value=mock_repo,
    ):
        actions = [
            {"type": "enqueue_job", "handler": "send_report", "payload": {"format": "pdf"}}
        ]
        executed, error = await execute_actions(
            actions=actions,
            record={},
            context=HookContext(app=None, account_id="acc-test"),
            session_factory=session_factory,
        )

    assert executed == 1
    assert error is None


@pytest.mark.asyncio
async def test_enqueue_job_missing_handler_returns_error() -> None:
    """enqueue_job without 'handler' records an error."""
    actions = [{"type": "enqueue_job"}]
    executed, error = await execute_actions(
        actions=actions, record={}, context=None, session_factory=None
    )
    assert executed == 0
    assert error is not None
    assert "handler" in error.lower()


# ---------------------------------------------------------------------------
# execute_actions — unknown action type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_action_type_is_skipped() -> None:
    """An unknown action type is skipped (counted as 0) but does not raise."""
    actions = [{"type": "definitely_not_real"}]
    executed, error = await execute_actions(
        actions=actions, record={}, context=None, session_factory=None
    )
    assert executed == 0
    assert error is None


# ---------------------------------------------------------------------------
# execute_actions — empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_actions_returns_zero() -> None:
    """Empty action list executes successfully with count=0."""
    executed, error = await execute_actions(
        actions=[], record={}, context=None, session_factory=None
    )
    assert executed == 0
    assert error is None


# ---------------------------------------------------------------------------
# execute_actions — first failure aborts chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_failure_aborts_remaining_actions() -> None:
    """If action N fails, actions N+1... are not executed."""
    call_count = 0

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def _failing_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise Exception("network error")

    mock_client.request = _failing_request

    with patch("httpx.AsyncClient", return_value=mock_client):
        actions = [
            {"type": "send_webhook", "url": "https://fails.example.com"},
            {"type": "send_webhook", "url": "https://should-not-run.example.com"},
        ]
        executed, error = await execute_actions(
            actions=actions, record={}, context=None, session_factory=None
        )

    assert executed == 0  # first action failed before it counted
    assert error is not None
    assert call_count == 1  # second action was never attempted
