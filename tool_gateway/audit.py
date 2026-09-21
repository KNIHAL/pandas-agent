"""Audit logging for the tool-gateway.

Every tool invocation (success or failure) is recorded as one JSON line.
Kept deliberately simple: append-only JSONL file, no external dependency.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


class AuditLogger:
    """Thread-safe append-only JSONL audit logger."""

    def __init__(self, log_path: str | Path = "tool_gateway/audit_log.jsonl") -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        tool_name: str,
        permission: str,
        success: bool,
        duration_ms: float,
        error_type: str | None = None,
        error_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "ts": time.time(),
            "tool_name": tool_name,
            "permission": permission,
            "success": success,
            "duration_ms": round(duration_ms, 2),
            "error_type": error_type,
            "error_message": error_message,
        }
        if extra:
            entry["extra"] = extra

        line = json.dumps(entry, default=str)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
