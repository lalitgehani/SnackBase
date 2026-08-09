"""Negative-assertion helpers for the security suite.

These helpers exist so cross-tenant tests read as intent ("this was denied",
"this leaked nothing") rather than as status-code boilerplate. The allowed
status set is always explicit at the call site so a test can require exactly
404 (isolation: the resource must not appear to exist) versus 403
(authorization: the resource exists but access is refused).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Protocol


class ResponseLike(Protocol):
    """Minimal structural type for the response objects the helpers accept."""

    status_code: int
    text: str


DEFAULT_DENIED_STATUSES: tuple[int, ...] = (401, 403, 404)


def _body_text(response: ResponseLike) -> str:
    """Return the response body as text, tolerating non-text payloads."""
    try:
        return response.text or ""
    except Exception:  # pragma: no cover - defensive, streaming/binary bodies
        return ""


def assert_no_leak(response: ResponseLike, *secret_markers: str) -> None:
    """Fail if any marker substring appears anywhere in the response body.

    Args:
        response: The response to inspect.
        *secret_markers: Marker substrings that must not be present.

    Raises:
        AssertionError: If any marker is found in the body.
    """
    body = _body_text(response)
    leaked = [marker for marker in secret_markers if marker and marker in body]
    if leaked:
        raise AssertionError(
            f"Response leaked secret marker(s) {leaked!r} "
            f"(status {response.status_code}): {body[:500]}"
        )


def assert_denied(
    response: ResponseLike,
    allowed: Sequence[int] | Iterable[int] = DEFAULT_DENIED_STATUSES,
    *,
    leak_markers: Sequence[str] = (),
) -> None:
    """Assert a response represents a denial, and leaked nothing.

    Args:
        response: The response to inspect.
        allowed: The exact set of status codes accepted as a denial. Pass a
            single-element tuple to require one specific code.
        leak_markers: Optional marker substrings that must not appear in the
            body even on an otherwise-correct denial status.

    Raises:
        AssertionError: If the status is outside ``allowed`` or a marker leaked.
    """
    allowed_set = tuple(allowed)
    if response.status_code not in allowed_set:
        raise AssertionError(
            f"Expected denial with status in {allowed_set}, "
            f"got {response.status_code}: {_body_text(response)[:500]}"
        )
    if leak_markers:
        assert_no_leak(response, *leak_markers)


def assert_allowed(response: ResponseLike, allowed: Sequence[int] = (200, 201)) -> None:
    """Assert a positive-control response succeeded.

    Positive controls matter as much as the attack itself: without them a test
    can "pass" simply because the feature is broken for everyone.
    """
    allowed_set = tuple(allowed)
    if response.status_code not in allowed_set:
        raise AssertionError(
            f"Expected success with status in {allowed_set}, "
            f"got {response.status_code}: {_body_text(response)[:500]}"
        )


def json_or_text(response: ResponseLike) -> Any:
    """Return the parsed JSON body, falling back to raw text."""
    parse = getattr(response, "json", None)
    if parse is not None:
        try:
            return parse()
        except Exception:
            pass
    return _body_text(response)
