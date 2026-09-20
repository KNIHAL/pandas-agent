"""Gateway core: validation + routing layer.

ToolGateway sits between agent-core and every registered tool. Agent-core
never calls a tool handler directly — it always goes through
ToolGateway.invoke(), which enforces the contract before/after the call.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from pydantic import BaseModel, ValidationError

from .audit import AuditLogger
from .contracts import FailureBehavior, Permission, ToolContract


class ToolError(BaseModel):
    type: str
    message: str
    details: dict[str, Any] = {}


class ToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error: ToolError | None = None
    duration_ms: float = 0.0


class PermissionDeniedError(Exception):
    """Raised when FailureBehavior.RAISE is set and permission is missing."""


class ToolGateway:
    """Registers tool contracts and mediates every call into them."""

    def __init__(
        self,
        granted_permissions: set[Permission] | None = None,
        audit_logger: AuditLogger | None = None,
        max_workers: int = 8,
    ) -> None:
        self._contracts: dict[str, ToolContract] = {}
        self._granted_permissions = granted_permissions or set()
        self._audit = audit_logger or AuditLogger()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def register(self, contract: ToolContract) -> None:
        if contract.name in self._contracts:
            raise ValueError(f"Tool '{contract.name}' is already registered.")
        self._contracts[contract.name] = contract

    def grant(self, permission: Permission) -> None:
        self._granted_permissions.add(permission)

    def revoke(self, permission: Permission) -> None:
        self._granted_permissions.discard(permission)

    def list_tools(self) -> list[str]:
        return sorted(self._contracts.keys())

    def invoke(self, tool_name: str, raw_input: dict[str, Any]) -> ToolResult:
        start = time.monotonic()
        contract = self._contracts.get(tool_name)

        if contract is None:
            return self._fail(
                tool_name=tool_name,
                permission="unknown",
                start=start,
                error_type="NOT_FOUND",
                message=f"No tool registered as '{tool_name}'.",
                failure_behavior=FailureBehavior.RETURN_ERROR,
            )

        # 1. Permission check
        if contract.permission not in self._granted_permissions:
            return self._fail(
                tool_name=tool_name,
                permission=contract.permission.value,
                start=start,
                error_type="PERMISSION_DENIED",
                message=f"Tool '{tool_name}' requires permission '{contract.permission.value}'.",
                failure_behavior=contract.failure_behavior,
            )

        # 2. Input validation
        try:
            validated_input = contract.input_schema(**raw_input)
        except ValidationError as e:
            return self._fail(
                tool_name=tool_name,
                permission=contract.permission.value,
                start=start,
                error_type="INVALID_INPUT",
                message=str(e),
                failure_behavior=contract.failure_behavior,
            )

        # 3. Execute with timeout, honoring RETRY_ONCE
        attempts = 2 if contract.failure_behavior == FailureBehavior.RETRY_ONCE else 1
        last_exc: Exception | None = None
        raw_output = None
        for attempt in range(attempts):
            try:
                raw_output = self._run_with_timeout(contract, validated_input)
                last_exc = None
                break
            except FutureTimeoutError:
                last_exc = TimeoutError(
                    f"Tool '{tool_name}' exceeded timeout of {contract.timeout_seconds}s."
                )
            except Exception as e:  # noqa: BLE001 - deliberately broad, gateway boundary
                last_exc = e

        if last_exc is not None:
            error_type = "TIMEOUT" if isinstance(last_exc, TimeoutError) else "EXECUTION_ERROR"
            if contract.failure_behavior == FailureBehavior.RAISE:
                self._audit.record(
                    tool_name=tool_name,
                    permission=contract.permission.value,
                    success=False,
                    duration_ms=(time.monotonic() - start) * 1000,
                    error_type=error_type,
                    error_message=str(last_exc),
                )
                raise last_exc
            return self._fail(
                tool_name=tool_name,
                permission=contract.permission.value,
                start=start,
                error_type=error_type,
                message=str(last_exc),
                failure_behavior=contract.failure_behavior,
            )

        # 4. Output validation
        try:
            if isinstance(raw_output, contract.output_schema):
                validated_output = raw_output
            else:
                validated_output = contract.output_schema(**raw_output)
        except ValidationError as e:
            return self._fail(
                tool_name=tool_name,
                permission=contract.permission.value,
                start=start,
                error_type="OUTPUT_VALIDATION",
                message=str(e),
                failure_behavior=contract.failure_behavior,
            )

        # 5. Limit enforcement (row truncation convention: output.truncate(max_rows))
        if contract.limits.max_rows is not None and hasattr(validated_output, "truncate"):
            validated_output.truncate(contract.limits.max_rows)  # type: ignore[attr-defined]

        duration_ms = (time.monotonic() - start) * 1000
        self._audit.record(
            tool_name=tool_name,
            permission=contract.permission.value,
            success=True,
            duration_ms=duration_ms,
        )
        return ToolResult(success=True, data=validated_output, duration_ms=duration_ms)

    def _run_with_timeout(self, contract: ToolContract, validated_input: BaseModel) -> Any:
        future = self._executor.submit(contract.handler, validated_input)
        return future.result(timeout=contract.timeout_seconds)

    def _fail(
        self,
        *,
        tool_name: str,
        permission: str,
        start: float,
        error_type: str,
        message: str,
        failure_behavior: FailureBehavior,
    ) -> ToolResult:
        duration_ms = (time.monotonic() - start) * 1000
        self._audit.record(
            tool_name=tool_name,
            permission=permission,
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=message,
        )
        return ToolResult(
            success=False,
            error=ToolError(type=error_type, message=message),
            duration_ms=duration_ms,
        )
