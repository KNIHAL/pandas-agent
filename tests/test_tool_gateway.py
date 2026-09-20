"""Gateway core tests — validation, permission, timeout, retry, not-found."""

import time

from pydantic import BaseModel

from tool_gateway.contracts import Permission, ToolContract
from tool_gateway.gateway import ToolGateway


class EchoIn(BaseModel):
    text: str


class EchoOut(BaseModel):
    text: str


def echo_handler(inp: EchoIn) -> EchoOut:
    return EchoOut(text=inp.text.upper())


def slow_handler(inp: EchoIn) -> EchoOut:
    time.sleep(0.5)
    return EchoOut(text=inp.text)


def make_gateway(tmp_path) -> ToolGateway:
    from tool_gateway.audit import AuditLogger

    gw = ToolGateway(
        granted_permissions={Permission.READ_DATA},
        audit_logger=AuditLogger(tmp_path / "audit_log.jsonl"),
    )
    gw.register(ToolContract(
        name="echo", purpose="Echo uppercased.",
        input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    gw.register(ToolContract(
        name="slow_echo", purpose="Slow echo, for timeout test.",
        input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, timeout_seconds=0.1, handler=slow_handler,
    ))
    gw.register(ToolContract(
        name="needs_write", purpose="Requires ungranted permission.",
        input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.WRITE_DATA, handler=echo_handler,
    ))
    return gw


def test_happy_path(tmp_path):
    gw = make_gateway(tmp_path)
    result = gw.invoke("echo", {"text": "hello"})
    assert result.success
    assert result.data.text == "HELLO"


def test_invalid_input(tmp_path):
    gw = make_gateway(tmp_path)
    result = gw.invoke("echo", {"wrong_field": 1})
    assert not result.success
    assert result.error.type == "INVALID_INPUT"


def test_permission_denied(tmp_path):
    gw = make_gateway(tmp_path)
    result = gw.invoke("needs_write", {"text": "hi"})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"


def test_timeout(tmp_path):
    gw = make_gateway(tmp_path)
    result = gw.invoke("slow_echo", {"text": "hi"})
    assert not result.success
    assert result.error.type == "TIMEOUT"


def test_not_found(tmp_path):
    gw = make_gateway(tmp_path)
    result = gw.invoke("does_not_exist", {"text": "hi"})
    assert not result.success
    assert result.error.type == "NOT_FOUND"
