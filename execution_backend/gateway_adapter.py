"""Wraps an ExecutionBackend as a tool_gateway ToolContract.

Mirrors agent_core/gateway_adapter.py's role: the boundary between this
module's own request/result shape and tool-gateway's ToolContract/ToolResult
pipeline. Actual gateway.register(...) call is left to the wiring code
(server.py) that owns the ToolGateway instance.
"""

from __future__ import annotations

from pydantic import BaseModel

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from .base import ExecutionBackend
from .contracts import ExecutionLimits, ExecutionRequest


class ExecuteCodeInput(BaseModel):
    code: str
    file_path: str | None = None


class ExecuteCodeOutput(BaseModel):
    success: bool
    result: object | None = None
    stdout: str = ""
    error_type: str | None = None
    error_message: str | None = None


def make_execute_code_contract(
    backend: ExecutionBackend,
    timeout_seconds: float = 30.0,
    max_memory_mb: int = 512,
) -> ToolContract:
    """Build the 'execute_code' ToolContract for a given ExecutionBackend."""

    def handler(inp: ExecuteCodeInput) -> ExecuteCodeOutput:
        result = backend.execute(
            ExecutionRequest(
                code=inp.code,
                file_path=inp.file_path,
                limits=ExecutionLimits(timeout_seconds=timeout_seconds, max_memory_mb=max_memory_mb),
            )
        )
        return ExecuteCodeOutput(
            success=result.success,
            result=result.result,
            stdout=result.stdout,
            error_type=result.error_type,
            error_message=result.error_message,
        )

    return ToolContract(
        name="execute_code",
        purpose="Run pandas/numpy/matplotlib/duckdb/scipy analysis code in a controlled local subprocess.",
        input_schema=ExecuteCodeInput,
        output_schema=ExecuteCodeOutput,
        permission=Permission.EXECUTE_CODE,
        timeout_seconds=timeout_seconds + 5.0,
        failure_behavior=FailureBehavior.RETURN_ERROR,
        handler=handler,
    )
