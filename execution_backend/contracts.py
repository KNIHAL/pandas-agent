"""Data contracts for the execution-backend module.

ExecutionRequest/ExecutionResult are the module's own request/response
shape, independent of tool_gateway.ToolContract — gateway_adapter.py wraps
these into a ToolContract for registration with tool-gateway.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionLimits(BaseModel):
    """Resource limits enforced by an ExecutionBackend for a single run."""

    timeout_seconds: float = Field(default=30.0, description="Wall-clock timeout.")
    max_memory_mb: int = Field(default=512, description="RSS memory limit for the run.")


class ExecutionRequest(BaseModel):
    code: str = Field(description="Python source. Must assign its final answer to 'result'.")
    file_path: str | None = Field(default=None, description="Optional data file path exposed to the code.")
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)


class ExecutionResult(BaseModel):
    success: bool = False
    result: Any | None = None
    stdout: str = ""
    error_type: str | None = None
    error_message: str | None = None
    duration_ms: float = 0.0
