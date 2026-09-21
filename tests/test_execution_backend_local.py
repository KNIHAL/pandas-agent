"""Tests for execution_backend.local_executor.LocalExecutor — subprocess
execution, security-violation short-circuit, timeout, and result shape.

Memory-limit enforcement is exercised with a small limit against real
allocation rather than mocked, so it stays honest about actual RSS behavior.
"""

from execution_backend.contracts import ExecutionLimits, ExecutionRequest
from execution_backend.local_executor import LocalExecutor


def run(code: str, timeout_seconds: float = 10.0, max_memory_mb: int = 512, file_path=None, poll_interval=0.02):
    executor = LocalExecutor(poll_interval=poll_interval)
    request = ExecutionRequest(
        code=code, file_path=file_path,
        limits=ExecutionLimits(timeout_seconds=timeout_seconds, max_memory_mb=max_memory_mb),
    )
    return executor.execute(request)


def test_simple_result_returns_success():
    result = run("result = 1 + 1")
    assert result.success
    assert result.result == 2


def test_stdout_is_captured():
    result = run("print('hello')\nresult = 1")
    assert result.success
    assert "hello" in result.stdout


def test_missing_result_variable_is_reported():
    result = run("x = 1")
    assert not result.success
    assert result.error_type == "NO_RESULT"


def test_dataframe_result_is_serialized_to_dict():
    result = run("import pandas as pd\nresult = pd.DataFrame({'a': [1, 2]})")
    assert result.success
    # Round-trips through JSON, so integer index keys become strings.
    assert result.result == {"a": {"0": 1, "1": 2}}


def test_runtime_exception_returns_execution_error():
    result = run("result = 1 / 0")
    assert not result.success
    assert result.error_type == "EXECUTION_ERROR"


def test_disallowed_import_is_rejected_before_running():
    result = run("import os\nresult = os.getcwd()")
    assert not result.success
    assert result.error_type == "SECURITY_VIOLATION"


def test_blocked_builtin_is_rejected_before_running():
    result = run("result = eval('1')")
    assert not result.success
    assert result.error_type == "SECURITY_VIOLATION"


def test_infinite_loop_is_killed_on_timeout():
    result = run("while True:\n    pass", timeout_seconds=0.3)
    assert not result.success
    assert result.error_type == "TIMEOUT"


def test_memory_limit_kills_runaway_allocation():
    # Allocates well past a tiny 20MB cap, then busy-loops so the poller has
    # a real window to observe the elevated RSS before the process exits.
    code = (
        "x = bytearray(200 * 1024 * 1024)\n"
        "s = 0\n"
        "for i in range(20_000_000):\n"
        "    s += i\n"
        "result = 1\n"
    )
    result = run(code, timeout_seconds=10.0, max_memory_mb=20, poll_interval=0.005)
    assert not result.success
    assert result.error_type in ("MEMORY_LIMIT", "TIMEOUT")
