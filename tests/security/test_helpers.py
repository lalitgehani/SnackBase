"""Unit tests for the security-suite assertion helpers (F1.2)."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from tests.security.helpers import (
    OWNER_CONTROL_KEY,
    assert_allowed,
    assert_denied,
    assert_no_leak,
    cross_tenant_matrix,
    json_or_text,
)


@dataclass
class StubResponse:
    """Minimal stand-in for an httpx Response."""

    status_code: int
    text: str = ""


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_assert_denied_passes_for_denial_statuses(status_code: int) -> None:
    assert_denied(StubResponse(status_code=status_code, text="{}"))


def test_assert_denied_raises_for_success() -> None:
    with pytest.raises(AssertionError, match="Expected denial"):
        assert_denied(StubResponse(status_code=200, text='{"secret": "x"}'))


def test_assert_denied_honours_explicit_allowed_set() -> None:
    """A test can require exactly 404 (isolation) rather than any denial."""
    assert_denied(StubResponse(status_code=404), allowed=(404,))
    with pytest.raises(AssertionError):
        assert_denied(StubResponse(status_code=403), allowed=(404,))


def test_assert_denied_flags_leak_on_correct_status() -> None:
    with pytest.raises(AssertionError, match="BETA-SECRET"):
        assert_denied(
            StubResponse(status_code=403, text="denied: BETA-SECRET"),
            leak_markers=("BETA-SECRET",),
        )


def test_assert_no_leak_raises_when_marker_present() -> None:
    with pytest.raises(AssertionError, match="BETA-SECRET"):
        assert_no_leak(StubResponse(status_code=200, text='{"v": "BETA-SECRET"}'), "BETA-SECRET")


def test_assert_no_leak_passes_when_marker_absent() -> None:
    assert_no_leak(StubResponse(status_code=200, text='{"v": "harmless"}'), "BETA-SECRET")


def test_assert_allowed_raises_for_denial() -> None:
    with pytest.raises(AssertionError, match="Expected success"):
        assert_allowed(StubResponse(status_code=403, text="nope"))


def test_json_or_text_falls_back_to_text() -> None:
    assert json_or_text(StubResponse(status_code=200, text="not json")) == "not json"


@dataclass
class RecordingClient:
    """Records the method/URL of every request instead of issuing it."""

    calls: list[tuple[str, str]] = field(default_factory=list)

    async def _record(self, method: str, url: str) -> StubResponse:
        self.calls.append((method, url))
        return StubResponse(status_code=404)

    async def get(self, url: str, **kwargs: Any) -> StubResponse:
        return await self._record("GET", url)

    async def post(self, url: str, json: Any = None, **kwargs: Any) -> StubResponse:
        return await self._record("POST", url)

    async def patch(self, url: str, json: Any = None, **kwargs: Any) -> StubResponse:
        return await self._record("PATCH", url)

    async def delete(self, url: str, **kwargs: Any) -> StubResponse:
        return await self._record("DELETE", url)


@pytest.mark.asyncio
async def test_cross_tenant_matrix_issues_expected_methods() -> None:
    recorder = RecordingClient()

    results = await cross_tenant_matrix(
        recorder,
        victim_url="/api/v1/records/vault/rec-1",
        victim_token="owner-token",
        attacker_token="attacker-token",
    )

    assert [method for method, _ in recorder.calls] == ["GET", "GET", "PATCH", "DELETE"]
    assert set(results) == {OWNER_CONTROL_KEY, "GET", "PATCH", "DELETE"}


@pytest.mark.asyncio
async def test_cross_tenant_matrix_adds_post_when_write_body_given() -> None:
    recorder = RecordingClient()

    results = await cross_tenant_matrix(
        recorder,
        victim_url="/api/v1/records/vault",
        victim_token="owner-token",
        attacker_token="attacker-token",
        write_body={"title": "forged"},
    )

    assert "POST" in results
    assert [method for method, _ in recorder.calls] == [
        "GET",
        "GET",
        "PATCH",
        "POST",
        "DELETE",
    ]
