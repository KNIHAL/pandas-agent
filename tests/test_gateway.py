"""Tests for tool_gateway.gateway.ToolGateway — the full invoke() pipeline:
permission enforcement, input/output validation, timeout + max_query_seconds,
row/size limits, retry, and both failure surfaces (ToolResult vs raised
exception).
"""

import time

import pytest
from pydantic import BaseModel

from tool_gateway.audit import AuditLogger
from tool_gateway.contracts import FailureBehavior, Permission, ToolContract, ToolLimits
from tool_gateway.errors import (
    InvalidInputError,
    OutputTooLargeError,
    PermissionDeniedError,
    ToolExecutionError,
    ToolTimeoutError,
)
from tool_gateway.gateway import ToolGateway


class EchoIn(BaseModel):
    text: str


class EchoOut(BaseModel):
    text: str


class ListOut(BaseModel):
    rows: list[int]

    def truncate(self, max_rows: int) -> None:
        self.rows = self.rows[:max_rows]


def echo_handler(inp: EchoIn) -> EchoOut:
    return EchoOut(text=inp.text.upper())


def slow_handler(inp: EchoIn) -> EchoOut:
    time.sleep(0.5)
    return EchoOut(text=inp.text)


def always_fails_handler(inp: EchoIn) -> EchoOut:
    raise RuntimeError("handler blew up")


def make_flaky_handler():
    """Fails on the first call, succeeds on the second — for RETRY_ONCE tests."""
    calls = {"count": 0}

    def handler(inp: EchoIn) -> EchoOut:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient failure")
        return EchoOut(text=inp.text)

    handler.calls = calls
    return handler


def rows_handler(inp: EchoIn) -> ListOut:
    return ListOut(rows=list(range(100)))


def new_gateway(tmp_path, granted=None) -> ToolGateway:
    return ToolGateway(
        granted_permissions=granted if granted is not None else {Permission.READ_DATA},
        audit_logger=AuditLogger(tmp_path / "audit.jsonl"),
    )


# ---------------------------------------------------------------------------
# Happy path / basic pipeline
# ---------------------------------------------------------------------------

def test_happy_path_returns_validated_output(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="echo", purpose="Echo uppercased.",
        input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))

    result = gw.invoke("echo", {"text": "hello"})

    assert result.success
    assert result.data.text == "HELLO"
    assert result.error is None
    assert result.duration_ms >= 0


def test_unknown_tool_returns_not_found(tmp_path):
    gw = new_gateway(tmp_path)
    result = gw.invoke("does_not_exist", {"text": "hi"})
    assert not result.success
    assert result.error.type == "NOT_FOUND"


def test_list_tools_returns_registered_names_sorted(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="zeta", purpose="z", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    gw.register(ToolContract(
        name="alpha", purpose="a", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    assert gw.list_tools() == ["alpha", "zeta"]


def test_get_contract_returns_registered_contract_by_name(tmp_path):
    gw = new_gateway(tmp_path)
    contract = ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    )
    gw.register(contract)
    assert gw.get_contract("echo") is contract
    assert gw.get_contract("does_not_exist") is None


def test_registering_duplicate_tool_name_raises_value_error(tmp_path):
    gw = new_gateway(tmp_path)
    contract = ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    )
    gw.register(contract)
    with pytest.raises(ValueError):
        gw.register(contract)


# ---------------------------------------------------------------------------
# Permission enforcement
# ---------------------------------------------------------------------------

def test_permission_denied_returns_error_by_default(tmp_path):
    gw = new_gateway(tmp_path, granted=set())
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    result = gw.invoke("echo", {"text": "hi"})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"


def test_permission_denied_raises_when_failure_behavior_is_raise(tmp_path):
    gw = new_gateway(tmp_path, granted=set())
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, failure_behavior=FailureBehavior.RAISE,
        handler=echo_handler,
    ))
    with pytest.raises(PermissionDeniedError):
        gw.invoke("echo", {"text": "hi"})


def test_grant_then_revoke_permission_changes_outcome(tmp_path):
    gw = new_gateway(tmp_path, granted=set())
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))

    assert not gw.invoke("echo", {"text": "hi"}).success

    gw.grant(Permission.READ_DATA)
    assert gw.invoke("echo", {"text": "hi"}).success

    gw.revoke(Permission.READ_DATA)
    assert not gw.invoke("echo", {"text": "hi"}).success


# ---------------------------------------------------------------------------
# Input / output validation
# ---------------------------------------------------------------------------

def test_invalid_input_returns_error_by_default(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    result = gw.invoke("echo", {"wrong_field": 1})
    assert not result.success
    assert result.error.type == "INVALID_INPUT"


def test_invalid_input_raises_when_failure_behavior_is_raise(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, failure_behavior=FailureBehavior.RAISE,
        handler=echo_handler,
    ))
    with pytest.raises(InvalidInputError):
        gw.invoke("echo", {"wrong_field": 1})


def test_handler_returning_dict_is_validated_against_output_schema(tmp_path):
    def dict_handler(inp: EchoIn) -> dict:
        return {"text": inp.text}

    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=dict_handler,
    ))
    result = gw.invoke("echo", {"text": "hi"})
    assert result.success
    assert result.data.text == "hi"


# ---------------------------------------------------------------------------
# Timeout / max_query_seconds
# ---------------------------------------------------------------------------

def test_timeout_returns_error_by_default(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="slow", purpose="Slow.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, timeout_seconds=0.1, handler=slow_handler,
    ))
    result = gw.invoke("slow", {"text": "hi"})
    assert not result.success
    assert result.error.type == "TIMEOUT"


def test_timeout_raises_typed_error_when_failure_behavior_is_raise(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="slow", purpose="Slow.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, timeout_seconds=0.1,
        failure_behavior=FailureBehavior.RAISE, handler=slow_handler,
    ))
    with pytest.raises(ToolTimeoutError):
        gw.invoke("slow", {"text": "hi"})


def test_max_query_seconds_tightens_timeout_below_default(tmp_path):
    # timeout_seconds is generous (5s) but max_query_seconds (0.1s) should win.
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="slow", purpose="Slow.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, timeout_seconds=5.0,
        limits=ToolLimits(max_query_seconds=0.1), handler=slow_handler,
    ))
    result = gw.invoke("slow", {"text": "hi"})
    assert not result.success
    assert result.error.type == "TIMEOUT"


# ---------------------------------------------------------------------------
# Row / output-size limits
# ---------------------------------------------------------------------------

def test_max_rows_truncates_output_and_marks_audit_extra(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    gw = new_gateway(tmp_path)
    gw._audit = AuditLogger(log_path)  # reuse same path to inspect after
    gw.register(ToolContract(
        name="rows", purpose="Rows.", input_schema=EchoIn, output_schema=ListOut,
        permission=Permission.READ_DATA, limits=ToolLimits(max_rows=5),
        handler=rows_handler,
    ))
    result = gw.invoke("rows", {"text": "hi"})
    assert result.success
    assert result.data.rows == [0, 1, 2, 3, 4]

    import json
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    last_entry = json.loads(lines[-1])
    assert last_entry.get("extra") == {"truncated": True}


def test_max_output_bytes_fails_when_output_too_large(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="rows", purpose="Rows.", input_schema=EchoIn, output_schema=ListOut,
        permission=Permission.READ_DATA, limits=ToolLimits(max_output_bytes=10),
        handler=rows_handler,
    ))
    result = gw.invoke("rows", {"text": "hi"})
    assert not result.success
    assert result.error.type == "OUTPUT_TOO_LARGE"


def test_max_output_bytes_raises_when_failure_behavior_is_raise(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="rows", purpose="Rows.", input_schema=EchoIn, output_schema=ListOut,
        permission=Permission.READ_DATA, limits=ToolLimits(max_output_bytes=10),
        failure_behavior=FailureBehavior.RAISE, handler=rows_handler,
    ))
    with pytest.raises(OutputTooLargeError):
        gw.invoke("rows", {"text": "hi"})


def test_max_rows_truncation_can_bring_output_under_byte_limit(tmp_path):
    # 100 rows would blow max_output_bytes, but truncating to 2 rows first
    # should bring it comfortably under.
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="rows", purpose="Rows.", input_schema=EchoIn, output_schema=ListOut,
        permission=Permission.READ_DATA,
        limits=ToolLimits(max_rows=2, max_output_bytes=200),
        handler=rows_handler,
    ))
    result = gw.invoke("rows", {"text": "hi"})
    assert result.success
    assert result.data.rows == [0, 1]


# ---------------------------------------------------------------------------
# Execution failure / retry / raise
# ---------------------------------------------------------------------------

def test_execution_error_returns_error_by_default(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="boom", purpose="Boom.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=always_fails_handler,
    ))
    result = gw.invoke("boom", {"text": "hi"})
    assert not result.success
    assert result.error.type == "EXECUTION_ERROR"
    assert "handler blew up" in result.error.message


def test_execution_error_raises_typed_error_when_failure_behavior_is_raise(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="boom", purpose="Boom.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, failure_behavior=FailureBehavior.RAISE,
        handler=always_fails_handler,
    ))
    with pytest.raises(ToolExecutionError):
        gw.invoke("boom", {"text": "hi"})


def test_retry_once_succeeds_after_first_transient_failure(tmp_path):
    flaky = make_flaky_handler()
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="flaky", purpose="Flaky.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, failure_behavior=FailureBehavior.RETRY_ONCE,
        handler=flaky,
    ))
    result = gw.invoke("flaky", {"text": "hi"})
    assert result.success
    assert result.data.text == "hi"
    assert flaky.calls["count"] == 2


def test_retry_once_still_fails_if_both_attempts_fail(tmp_path):
    gw = new_gateway(tmp_path)
    gw.register(ToolContract(
        name="boom", purpose="Boom.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, failure_behavior=FailureBehavior.RETRY_ONCE,
        handler=always_fails_handler,
    ))
    result = gw.invoke("boom", {"text": "hi"})
    assert not result.success
    assert result.error.type == "EXECUTION_ERROR"
