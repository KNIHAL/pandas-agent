"""Tests for tool_gateway.errors — typed exception mapping."""

import pytest

from tool_gateway.errors import (
    ERROR_TYPE_TO_EXCEPTION,
    InvalidInputError,
    OutputTooLargeError,
    OutputValidationError,
    PermissionDeniedError,
    ToolExecutionError,
    ToolGatewayError,
    ToolNotFoundError,
    ToolTimeoutError,
    exception_for,
)


@pytest.mark.parametrize(
    "error_type,expected_cls",
    [
        ("NOT_FOUND", ToolNotFoundError),
        ("PERMISSION_DENIED", PermissionDeniedError),
        ("INVALID_INPUT", InvalidInputError),
        ("TIMEOUT", ToolTimeoutError),
        ("EXECUTION_ERROR", ToolExecutionError),
        ("OUTPUT_VALIDATION", OutputValidationError),
        ("OUTPUT_TOO_LARGE", OutputTooLargeError),
    ],
)
def test_exception_for_maps_known_error_types(error_type, expected_cls):
    exc = exception_for(error_type, "boom")
    assert isinstance(exc, expected_cls)
    assert isinstance(exc, ToolGatewayError)
    assert str(exc) == "boom"
    assert exc.error_type == error_type


def test_exception_for_unknown_type_falls_back_to_base_class():
    exc = exception_for("SOMETHING_NEW", "mystery failure")
    assert type(exc) is ToolGatewayError
    assert str(exc) == "mystery failure"


def test_tool_timeout_error_is_also_a_builtin_timeout_error():
    # So callers that only catch builtin TimeoutError still catch this.
    exc = exception_for("TIMEOUT", "too slow")
    assert isinstance(exc, TimeoutError)


def test_every_registered_exception_has_a_unique_error_type():
    error_types = list(ERROR_TYPE_TO_EXCEPTION.keys())
    assert len(error_types) == len(set(error_types))
