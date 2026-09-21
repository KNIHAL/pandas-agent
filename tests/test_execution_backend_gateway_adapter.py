"""Tests for execution_backend.gateway_adapter — wiring LocalExecutor into
a real ToolGateway via the execute_code ToolContract."""

from execution_backend.gateway_adapter import make_execute_code_contract
from execution_backend.local_executor import LocalExecutor
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


def new_gateway_with_execute_code(**contract_kwargs) -> ToolGateway:
    gw = ToolGateway(granted_permissions={Permission.EXECUTE_CODE})
    gw.register(make_execute_code_contract(LocalExecutor(), **contract_kwargs))
    return gw


def test_execute_code_tool_runs_through_gateway():
    gw = new_gateway_with_execute_code()
    result = gw.invoke("execute_code", {"code": "result = 2 + 2"})
    assert result.success
    assert result.data.success
    assert result.data.result == 4


def test_execute_code_tool_reports_security_violation_via_gateway():
    gw = new_gateway_with_execute_code()
    result = gw.invoke("execute_code", {"code": "import os\nresult = 1"})
    assert result.success  # gateway call itself succeeded
    assert not result.data.success
    assert result.data.error_type == "SECURITY_VIOLATION"


def test_execute_code_denied_without_permission():
    gw = ToolGateway(granted_permissions=set())
    gw.register(make_execute_code_contract(LocalExecutor()))
    result = gw.invoke("execute_code", {"code": "result = 1"})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
