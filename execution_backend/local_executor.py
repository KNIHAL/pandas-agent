"""V1 ExecutionBackend: local subprocess isolation.

Layers:
  1. AST validation (validator.py) before anything runs.
  2. Restricted __builtins__ inside the worker subprocess (_worker.py).
  3. Wall-clock timeout + RSS memory polling from the parent, killing the
     worker process if either is exceeded.

NOT a hardened security sandbox — this is process isolation plus static/
runtime restrictions, not a seccomp/VM-grade boundary. Don't claim it is.
Stronger isolation (Docker/VM/Causly-hosted executor) is future work, same
ExecutionBackend interface.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from .base import ExecutionBackend
from .contracts import ExecutionRequest, ExecutionResult
from .validator import CodeValidationError, validate


class LocalExecutor(ExecutionBackend):
    def __init__(self, poll_interval: float = 0.05) -> None:
        self._poll_interval = poll_interval

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        start = time.monotonic()

        try:
            validate(request.code)
        except CodeValidationError as e:
            return ExecutionResult(
                success=False,
                error_type="SECURITY_VIOLATION",
                error_message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "request.json"
            res_path = Path(tmp) / "result.json"
            req_path.write_text(
                json.dumps({"code": request.code, "file_path": request.file_path}),
                encoding="utf-8",
            )

            proc = subprocess.Popen(
                [sys.executable, "-m", "execution_backend._worker", str(req_path), str(res_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            killed_reason = self._supervise(proc, request.limits.timeout_seconds, request.limits.max_memory_mb, start)
            duration_ms = (time.monotonic() - start) * 1000

            if killed_reason == "TIMEOUT":
                return ExecutionResult(
                    success=False, error_type="TIMEOUT",
                    error_message=f"Execution exceeded {request.limits.timeout_seconds}s timeout.",
                    duration_ms=duration_ms,
                )
            if killed_reason == "MEMORY_LIMIT":
                return ExecutionResult(
                    success=False, error_type="MEMORY_LIMIT",
                    error_message=f"Execution exceeded {request.limits.max_memory_mb}MB memory limit.",
                    duration_ms=duration_ms,
                )

            if not res_path.exists():
                return ExecutionResult(
                    success=False, error_type="EXECUTION_ERROR",
                    error_message=f"Worker process exited (code {proc.returncode}) without producing a result.",
                    duration_ms=duration_ms,
                )

            data = json.loads(res_path.read_text(encoding="utf-8"))
            data.pop("duration_ms", None)
            return ExecutionResult(duration_ms=duration_ms, **data)

    def _supervise(
        self, proc: subprocess.Popen, timeout_seconds: float, max_memory_mb: int, start: float
    ) -> str | None:
        try:
            ps_proc: psutil.Process | None = psutil.Process(proc.pid)
        except psutil.NoSuchProcess:
            ps_proc = None

        while True:
            if proc.poll() is not None:
                return None

            if time.monotonic() - start > timeout_seconds:
                self._kill_tree(proc, ps_proc)
                return "TIMEOUT"

            if ps_proc is not None:
                mem_mb = self._tree_memory_mb(ps_proc)
                if mem_mb > max_memory_mb:
                    self._kill_tree(proc, ps_proc)
                    return "MEMORY_LIMIT"

            time.sleep(self._poll_interval)

    @staticmethod
    def _tree_memory_mb(ps_proc: psutil.Process) -> float:
        """Total RSS across ps_proc and all its descendants.

        On Windows, `.venv\\Scripts\\python.exe` can be a launcher stub that
        re-execs the real interpreter as a child process — the stub itself
        stays near-idle, so monitoring only its own RSS misses the actual
        work entirely. Summing the whole tree covers both that case and the
        common case where the worker is the process itself (no children).
        """
        try:
            total = ps_proc.memory_info().rss
            for child in ps_proc.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except psutil.NoSuchProcess:
                    continue
        except psutil.NoSuchProcess:
            return 0.0
        return total / (1024 * 1024)

    @staticmethod
    def _kill_tree(proc: subprocess.Popen, ps_proc: psutil.Process | None) -> None:
        if ps_proc is not None:
            try:
                children = ps_proc.children(recursive=True)
            except psutil.NoSuchProcess:
                children = []
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    continue
        proc.kill()
        proc.wait()
