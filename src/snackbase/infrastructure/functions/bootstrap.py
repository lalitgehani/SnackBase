"""Bootstrap script executed inside the function venv.

Reads a JSON invoke payload from stdin, loads the user entrypoint,
calls ``handler(req)``, and prints a result envelope to stdout.

Streaming protocol (when handler returns Response with stream):
  line 1: envelope JSON with streaming=true (no body)
  next:   {"type":"chunk","data":"..."} per chunk
  last:   {"type":"end"}
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any


def _install_runtime_guards() -> None:
    """Install SSRF egress policy before user code imports httpx."""
    try:
        from snackbase_fn.egress_install import install_egress_policy

        install_egress_policy()
    except Exception:
        # Best-effort; continue so handler can still run offline
        pass


def _load_handler(workdir: Path, entrypoint: str) -> Any:
    entry_path = workdir / entrypoint
    if not entry_path.exists():
        raise FileNotFoundError(f"Entrypoint not found: {entrypoint}")
    module_name = "_snackbase_user_handler"
    spec = importlib.util.spec_from_file_location(module_name, entry_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load entrypoint: {entrypoint}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    workdir_str = str(workdir)
    if workdir_str not in sys.path:
        sys.path.insert(0, workdir_str)
    spec.loader.exec_module(module)
    handler = getattr(module, "handler", None)
    if handler is None or not callable(handler):
        raise AttributeError("Entrypoint must define a callable handler(req)")
    return handler


def _response_to_envelope(result: Any) -> dict[str, Any]:
    from snackbase_fn.response import Response

    if isinstance(result, Response):
        return result.to_envelope()
    if isinstance(result, dict) and "http_status" in result:
        return {
            "status": "success",
            "http_status": int(result.get("http_status", 200)),
            "headers": result.get("headers") or {},
            "body": result.get("body"),
            "streaming": False,
        }
    return {
        "status": "success",
        "http_status": 200,
        "headers": {"content-type": "application/json"},
        "body": result,
        "streaming": False,
    }


async def _call_handler(handler: Any, req: Any) -> Any:
    result = handler(req)
    if inspect.isawaitable(result):
        return await result
    return result


def _emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, default=str))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _emit_stream(result: Any) -> int:
    """Emit streaming protocol lines for a Response with stream."""
    envelope = {
        "status": "success",
        "http_status": result.status_code,
        "headers": result.headers,
        "body": None,
        "streaming": True,
        "media_type": result.media_type,
        "used_admin_client": os.environ.get("FN_USED_ADMIN_CLIENT") == "1",
    }
    _emit(envelope)

    stream_obj: Any = result.stream
    try:
        if inspect.isasyncgen(stream_obj) or hasattr(stream_obj, "__anext__"):

            async def _pump(agen: Any) -> None:
                async for chunk in agen:
                    if isinstance(chunk, bytes):
                        data = chunk.decode("utf-8", errors="replace")
                    else:
                        data = str(chunk)
                    _emit({"type": "chunk", "data": data})

            asyncio.run(_pump(stream_obj))
        else:
            for chunk in stream_obj:
                if isinstance(chunk, bytes):
                    data = chunk.decode("utf-8", errors="replace")
                else:
                    data = str(chunk)
                _emit({"type": "chunk", "data": data})
        _emit({"type": "end"})
        return 0
    except Exception as exc:
        _emit({"type": "error", "error": str(exc)})
        _emit({"type": "end"})
        return 1


def main() -> int:
    _install_runtime_guards()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw else {}
        workdir = Path(payload.get("workdir") or os.getcwd())
        entrypoint = payload.get("entrypoint") or "handler.py"

        from snackbase_fn.request import Request
        from snackbase_fn.response import Response

        req = Request.from_payload(payload.get("request") or {})
        handler = _load_handler(workdir, entrypoint)
        result = asyncio.run(_call_handler(handler, req))

        if isinstance(result, Response) and result.stream is not None:
            return _emit_stream(result)

        envelope = _response_to_envelope(result)
        envelope["used_admin_client"] = os.environ.get("FN_USED_ADMIN_CLIENT") == "1"
        _emit(envelope)
        return 0
    except Exception as exc:
        err = {
            "status": "failed",
            "http_status": 500,
            "headers": {},
            "body": {"error": str(exc)},
            "error_message": str(exc),
            "traceback": traceback.format_exc()[-4000:],
            "used_admin_client": os.environ.get("FN_USED_ADMIN_CLIENT") == "1",
            "streaming": False,
        }
        _emit(err)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
