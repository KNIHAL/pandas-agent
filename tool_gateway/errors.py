"""Typed exceptions the gateway can raise when a contract's failure_behavior
is FailureBehavior.RAISE. Each maps 1:1 to a ToolError.type string so the
error surface is identical whether the caller gets an exception or a
ToolResult.
"""

from __future__ import annotations


class ToolGatewayError(Exception):
    """Base class for all gateway-raised errors."""

    error_type = "GATEWAY_ERROR"


class ToolNotFoundError(ToolGatewayError):
    error_type = "NOT_FOUND"


class PermissionDeniedError(ToolGatewayError):
    error_type = "PERMISSION_DENIED"


class InvalidInputError(ToolGatewayError):
    error_type = "INVALID_INPUT"


class ToolTimeoutError(ToolGatewayError, TimeoutError):
    error_type = "TIMEOUT"


class ToolExecutionError(ToolGatewayError):
    error_type = "EXECUTION_ERROR"


class OutputValidationError(ToolGatewayError):
    error_type = "OUTPUT_VALIDATION"


class OutputTooLargeError(ToolGatewayError):
    error_type = "OUTPUT_TOO_LARGE"


ERROR_TYPE_TO_EXCEPTION: dict[str, type[ToolGatewayError]] = {
    cls.error_type: cls  # type: ignore[misc]
    for cls in (
        ToolNotFoundError,
        PermissionDeniedError,
        InvalidInputError,
        ToolTimeoutError,
        ToolExecutionError,
        OutputValidationError,
        OutputTooLargeError,
    )
}


def exception_for(error_type: str, message: str) -> ToolGatewayError:
    """Look up the typed exception for an error_type, falling back to the base class."""
    cls = ERROR_TYPE_TO_EXCEPTION.get(error_type, ToolGatewayError)
    return cls(message)
