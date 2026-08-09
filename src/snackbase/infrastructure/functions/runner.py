"""Subprocess runner for tenant function code."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.functions.redaction import truncate_text
from snackbase.infrastructure.functions.sandbox import (
    SandboxUnavailableError,
    create_filesystem_confinement,
    preexec_hook,
    resolve_sandbox_mode,
    resource_limit_hook,
)

logger = get_logger(__name__)

_BOOTSTRAP_PATH = Path(__file__).resolve().parent / "bootstrap.py"


@dataclass
class InvokeResult:
    """Outcome of a function subprocess invoke."""

    status: str  # success | failed | timeout
    http_status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    duration_ms: int = 0
    used_admin_client: bool = False
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    streaming: bool = False
    stream_chunks: list[str] = field(default_factory=list)
    media_type: str | None = None


class FunctionRunner:
    """Execute a function version in an isolated subprocess."""

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        streaming_timeout_seconds: int | None = None,
        stdout_max_bytes: int = 65_536,
        memory_limit_mb: int | None = None,
        sandbox_mode: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.streaming_timeout_seconds = streaming_timeout_seconds or max(
            timeout_seconds, 120
        )
        self.stdout_max_bytes = stdout_max_bytes
        settings = get_settings()
        self.memory_limit_mb = memory_limit_mb or settings.function_memory_limit_mb
        self.sandbox_mode = sandbox_mode or resolve_sandbox_mode(settings)
        # Persistent pushback buffer for stdout line reads (survives across lines)
        self._stdout_buf = b""

    def invoke(
        self,
        *,
        env_path: str | Path,
        source_files: dict[str, str],
        entrypoint: str,
        request_payload: dict[str, Any],
        extra_env: dict[str, str] | None = None,
        execution_id: str | None = None,
    ) -> InvokeResult:
        """Run the function and return an InvokeResult.

        Supports the bootstrap streaming protocol: first envelope line may set
        ``streaming: true``, followed by chunk/end lines.
        """
        exec_id = execution_id or str(uuid.uuid4())
        # Resolve env_path to absolute before subprocess: relative paths are
        # stored as "./sb_data/function_envs/...", but Popen uses cwd=tempdir,
        # so a relative bin/python fails with ENOENT after the chdir.
        env_root = Path(env_path)
        if not env_root.is_absolute():
            env_root = Path.cwd() / env_root
        env_root = env_root.resolve()
        # Keep the venv's bin/python path (do not resolve the symlink) so
        # site-packages and sys.prefix stay bound to the function env.
        env_python = env_root / "bin" / "python"
        if not env_python.exists():
            return InvokeResult(
                status="failed",
                http_status=500,
                error_message=f"Function environment not found: {env_path}",
                execution_id=exec_id,
            )

        workdir = Path(tempfile.mkdtemp(prefix="sb_fn_"))
        start = time.monotonic()
        self._stdout_buf = b""
        try:
            for rel_path, content in source_files.items():
                safe_rel = Path(rel_path)
                if safe_rel.is_absolute() or ".." in safe_rel.parts:
                    return InvokeResult(
                        status="failed",
                        http_status=400,
                        error_message=f"Invalid source path: {rel_path}",
                        execution_id=exec_id,
                    )
                target = workdir / safe_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            bootstrap_dest = workdir / "_snackbase_bootstrap.py"
            shutil.copy2(_BOOTSTRAP_PATH, bootstrap_dest)

            payload = {
                "workdir": str(workdir),
                "entrypoint": entrypoint,
                "request": request_payload,
            }
            stdin_data = json.dumps(payload).encode("utf-8")
            child_env = self._build_child_env(extra_env or {}, exec_id)

            try:
                confinement = create_filesystem_confinement(
                    env_root=env_root, workdir=workdir, mode=self.sandbox_mode
                )
            except SandboxUnavailableError as exc:
                return InvokeResult(
                    status="failed",
                    http_status=500,
                    error_message=str(exc),
                    execution_id=exec_id,
                    duration_ms=int((time.monotonic() - start) * 1000),
                )

            try:
                proc = subprocess.Popen(
                    [str(env_python), "-I", str(bootstrap_dest)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(workdir),
                    env=child_env,
                    start_new_session=True,
                    bufsize=0,
                    # The ruleset fd has to survive into the child, which applies
                    # it to itself just before exec.
                    pass_fds=() if confinement is None else (confinement.fd,),
                    preexec_fn=preexec_hook(  # noqa: PLW1509
                        confinement=confinement,
                        limits=resource_limit_hook(
                            memory_mb=self.memory_limit_mb,
                            cpu_seconds=self.timeout_seconds + 5,
                        ),
                    ),
                )
            except OSError as exc:
                return InvokeResult(
                    status="failed",
                    http_status=500,
                    error_message=f"Failed to start function process: {exc}",
                    execution_id=exec_id,
                    duration_ms=int((time.monotonic() - start) * 1000),
                )
            finally:
                if confinement is not None:
                    confinement.close()

            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None

            try:
                proc.stdin.write(stdin_data)
                proc.stdin.close()
            except BrokenPipeError:
                pass

            # Read first line (envelope) with overall timeout
            deadline = start + self.timeout_seconds
            try:
                first_line = self._readline_with_deadline(proc, deadline)
            except TimeoutError:
                return self._timeout_result(proc, start, exec_id, streaming=False)

            if first_line is None:
                stderr_b = proc.stderr.read() if proc.stderr else b""
                return InvokeResult(
                    status="failed",
                    http_status=500,
                    stderr=truncate_text(
                        stderr_b.decode("utf-8", errors="replace"),
                        self.stdout_max_bytes,
                    )
                    or "",
                    error_message="Function produced no output",
                    duration_ms=int((time.monotonic() - start) * 1000),
                    execution_id=exec_id,
                )

            try:
                envelope = json.loads(first_line)
            except json.JSONDecodeError:
                # Fallback: collect remaining and parse as before
                rest = proc.stdout.read().decode("utf-8", errors="replace")
                stderr_b = proc.stderr.read()
                proc.wait(timeout=5)
                return self._parse_output(
                    stdout=first_line + "\n" + rest,
                    stderr=stderr_b.decode("utf-8", errors="replace"),
                    returncode=proc.returncode or 0,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    execution_id=exec_id,
                )

            if envelope.get("streaming"):
                stream_deadline = start + self.streaming_timeout_seconds
                chunks: list[str] = []
                stdout_parts = [first_line]
                try:
                    while True:
                        line = self._readline_with_deadline(proc, stream_deadline)
                        if line is None:
                            break
                        stdout_parts.append(line)
                        try:
                            msg = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if msg.get("type") == "chunk":
                            chunks.append(str(msg.get("data") or ""))
                        elif msg.get("type") == "error":
                            envelope["error_message"] = str(msg.get("error") or "stream error")
                            envelope["status"] = "failed"
                            envelope["http_status"] = 500
                        elif msg.get("type") == "end":
                            break
                except TimeoutError:
                    self._kill_process_group(proc)
                    duration_ms = int((time.monotonic() - start) * 1000)
                    stderr_b = b""
                    try:
                        stderr_b = proc.stderr.read() if proc.stderr else b""
                    except Exception:
                        pass
                    return InvokeResult(
                        status="timeout",
                        http_status=504,
                        headers={
                            str(k): str(v) for k, v in (envelope.get("headers") or {}).items()
                        },
                        body="".join(chunks) if chunks else None,
                        stream_chunks=chunks,
                        streaming=True,
                        stdout=truncate_text("\n".join(stdout_parts), self.stdout_max_bytes) or "",
                        stderr=truncate_text(
                            stderr_b.decode("utf-8", errors="replace"),
                            self.stdout_max_bytes,
                        )
                        or "",
                        error_message=(
                            f"Function stream timed out after "
                            f"{self.streaming_timeout_seconds}s"
                        ),
                        duration_ms=duration_ms,
                        execution_id=exec_id,
                        media_type=envelope.get("media_type"),
                    )

                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._kill_process_group(proc)

                stderr_b = proc.stderr.read() if proc.stderr else b""
                duration_ms = int((time.monotonic() - start) * 1000)
                status = str(envelope.get("status") or "success")
                if status not in {"success", "failed", "timeout"}:
                    status = "success"
                return InvokeResult(
                    status=status,
                    http_status=int(envelope.get("http_status") or 200),
                    headers={
                        str(k): str(v) for k, v in (envelope.get("headers") or {}).items()
                    },
                    body="".join(chunks),
                    stream_chunks=chunks,
                    streaming=True,
                    stdout=truncate_text("\n".join(stdout_parts), self.stdout_max_bytes) or "",
                    stderr=truncate_text(
                        stderr_b.decode("utf-8", errors="replace"),
                        self.stdout_max_bytes,
                    )
                    or "",
                    error_message=envelope.get("error_message"),
                    duration_ms=duration_ms,
                    used_admin_client=bool(envelope.get("used_admin_client")),
                    execution_id=exec_id,
                    media_type=envelope.get("media_type"),
                )

            # Non-streaming: read rest of stdout
            rest = proc.stdout.read().decode("utf-8", errors="replace")
            try:
                proc.wait(timeout=max(1, int(deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                return self._timeout_result(proc, start, exec_id, streaming=False)

            stderr_b = proc.stderr.read() if proc.stderr else b""
            duration_ms = int((time.monotonic() - start) * 1000)
            return self._parse_envelope(
                envelope=envelope,
                stdout=first_line + ("\n" + rest if rest else ""),
                stderr=stderr_b.decode("utf-8", errors="replace"),
                returncode=proc.returncode or 0,
                duration_ms=duration_ms,
                execution_id=exec_id,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def iter_stream_chunks(self, result: InvokeResult) -> Iterator[bytes]:
        """Yield stream chunks as bytes for StreamingResponse."""
        for chunk in result.stream_chunks:
            yield chunk.encode("utf-8") if isinstance(chunk, str) else bytes(chunk)

    def _readline_with_deadline(
        self, proc: subprocess.Popen[bytes], deadline: float
    ) -> str | None:
        """Read one stdout line with pushback buffer, raising TimeoutError past deadline.

        Uses ``self._stdout_buf`` so multi-line reads after process exit do not
        discard remainder bytes after the first newline.
        """
        assert proc.stdout is not None
        import select

        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("deadline exceeded")

            # Serve a complete line from the pushback buffer first
            if b"\n" in self._stdout_buf:
                line, _, self._stdout_buf = self._stdout_buf.partition(b"\n")
                return line.decode("utf-8", errors="replace")

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("deadline exceeded")

            exited = proc.poll() is not None
            if exited:
                # Drain all remaining stdout into the buffer
                chunk = proc.stdout.read()
                if chunk:
                    self._stdout_buf += chunk
                    if b"\n" in self._stdout_buf:
                        line, _, self._stdout_buf = self._stdout_buf.partition(b"\n")
                        return line.decode("utf-8", errors="replace")
                # No more data and no complete line
                if self._stdout_buf:
                    line = self._stdout_buf
                    self._stdout_buf = b""
                    return line.decode("utf-8", errors="replace")
                return None

            rlist, _, _ = select.select(
                [proc.stdout], [], [], min(0.1, max(0.01, remaining))
            )
            if not rlist:
                continue
            # Read available bytes (avoid 1-byte loop for performance)
            chunk = proc.stdout.read(4096)
            if not chunk:
                # EOF without process exit yet — brief spin
                continue
            self._stdout_buf += chunk

    def _timeout_result(
        self,
        proc: subprocess.Popen[bytes],
        start: float,
        exec_id: str,
        *,
        streaming: bool,
    ) -> InvokeResult:
        self._kill_process_group(proc)
        stdout_b, stderr_b = b"", b""
        try:
            out = proc.communicate(timeout=2)
            stdout_b, stderr_b = out[0] or b"", out[1] or b""
        except Exception:
            pass
        return InvokeResult(
            status="timeout",
            http_status=504,
            stdout=truncate_text(
                stdout_b.decode("utf-8", errors="replace"), self.stdout_max_bytes
            )
            or "",
            stderr=truncate_text(
                stderr_b.decode("utf-8", errors="replace"), self.stdout_max_bytes
            )
            or "",
            error_message=f"Function timed out after {self.timeout_seconds}s",
            duration_ms=int((time.monotonic() - start) * 1000),
            execution_id=exec_id,
            streaming=streaming,
        )

    def _build_child_env(self, extra_env: dict[str, str], execution_id: str) -> dict[str, str]:
        path = os.environ.get("PATH", "/usr/bin:/bin")
        child: dict[str, str] = {
            "PATH": path,
            "HOME": tempfile.gettempdir(),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "FN_EXECUTION_ID": execution_id,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        allowed_prefixes = ("SNACKBASE_", "FN_", "HTTP_", "HTTPS_")
        reserved_block = {
            "SNACKBASE_ENCRYPTION_KEY",
            "SNACKBASE_SECRET_KEY",
            "SNACKBASE_DATABASE_URL",
        }
        for key, value in extra_env.items():
            if key in reserved_block:
                continue
            if key.startswith(allowed_prefixes) or key in {
                "PATH",
                "HOME",
                "TMPDIR",
                "TEMP",
                "TMP",
            }:
                child[key] = value
            elif key.isupper() and not key.startswith("SNACKBASE_"):
                child[key] = value
        return child

    @staticmethod
    def _kill_process_group(proc: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass

    def _parse_envelope(
        self,
        *,
        envelope: dict[str, Any],
        stdout: str,
        stderr: str,
        returncode: int,
        duration_ms: int,
        execution_id: str,
    ) -> InvokeResult:
        stdout_t = truncate_text(stdout, self.stdout_max_bytes) or ""
        stderr_t = truncate_text(stderr, self.stdout_max_bytes) or ""
        status = str(envelope.get("status") or ("success" if returncode == 0 else "failed"))
        if status not in {"success", "failed", "timeout"}:
            status = "failed" if returncode != 0 else "success"
        http_status = int(envelope.get("http_status") or (200 if status == "success" else 500))
        headers = {str(k): str(v) for k, v in (envelope.get("headers") or {}).items()}
        return InvokeResult(
            status=status,
            http_status=http_status,
            headers=headers,
            body=envelope.get("body"),
            stdout=stdout_t,
            stderr=stderr_t,
            error_message=envelope.get("error_message"),
            duration_ms=duration_ms,
            used_admin_client=bool(envelope.get("used_admin_client")),
            execution_id=execution_id,
            streaming=bool(envelope.get("streaming")),
            media_type=envelope.get("media_type"),
        )

    def _parse_output(
        self,
        *,
        stdout: str,
        stderr: str,
        returncode: int,
        duration_ms: int,
        execution_id: str,
    ) -> InvokeResult:
        stdout_t = truncate_text(stdout, self.stdout_max_bytes) or ""
        stderr_t = truncate_text(stderr, self.stdout_max_bytes) or ""
        envelope: dict[str, Any] | None = None
        for line in reversed(stdout.strip().splitlines() if stdout.strip() else []):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                envelope = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if envelope is None:
            return InvokeResult(
                status="failed",
                http_status=500,
                stdout=stdout_t,
                stderr=stderr_t,
                error_message="Function produced no parseable result envelope",
                duration_ms=duration_ms,
                execution_id=execution_id,
            )
        return self._parse_envelope(
            envelope=envelope,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            duration_ms=duration_ms,
            execution_id=execution_id,
        )
