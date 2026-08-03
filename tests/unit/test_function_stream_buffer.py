"""Unit tests for runner stdout pushback buffer (streaming multi-line)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from snackbase.infrastructure.functions.runner import FunctionRunner


def test_readline_pushback_keeps_remainder_after_exit() -> None:
    """When process exits with multiple lines buffered, all lines are returned."""
    runner = FunctionRunner(timeout_seconds=5)
    runner._stdout_buf = b""

    lines = [
        json.dumps({"status": "success", "streaming": True, "http_status": 200, "headers": {}}),
        json.dumps({"type": "chunk", "data": "one"}),
        json.dumps({"type": "chunk", "data": "two"}),
        json.dumps({"type": "chunk", "data": "three"}),
        json.dumps({"type": "end"}),
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")

    proc = MagicMock()
    # First poll: still running then exit after first read
    state = {"reads": 0, "data": payload}

    def poll():
        # Exit after first read attempt that gets data
        return 0 if state["reads"] > 0 else None

    def read(n: int = -1):
        state["reads"] += 1
        if not state["data"]:
            return b""
        if n is None or n < 0:
            out = state["data"]
            state["data"] = b""
            return out
        out = state["data"][:n]
        state["data"] = state["data"][n:]
        return out

    proc.poll = poll
    proc.stdout = MagicMock()
    proc.stdout.read = read

    # Simulate: process exits immediately with all data available
    proc.poll = lambda: 0
    proc.stdout.read = lambda n=-1: (
        (__import__("sys"), state).__getitem__(1) or state
    ) and (state.update({"tmp": state["data"]}) or True) and (
        state.__setitem__("data", b"") or state.pop("tmp")
    )

    # Simpler: put all data in buffer and process exited
    runner._stdout_buf = payload
    proc.poll = lambda: 0
    proc.stdout.read = lambda *a, **k: b""

    deadline = __import__("time").monotonic() + 5
    got = []
    while True:
        line = runner._readline_with_deadline(proc, deadline)
        if line is None:
            break
        got.append(line)

    assert len(got) == 5
    assert json.loads(got[0])["streaming"] is True
    assert json.loads(got[1])["data"] == "one"
    assert json.loads(got[2])["data"] == "two"
    assert json.loads(got[3])["data"] == "three"
    assert json.loads(got[4])["type"] == "end"
