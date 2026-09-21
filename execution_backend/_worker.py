"""Subprocess entry point for LocalExecutor.

Invoked as: python -m execution_backend._worker <request.json> <result.json>

Runs in its own process so LocalExecutor can enforce wall-clock timeout and
memory limits from outside (kill the process) rather than trying to interrupt
exec() from within the same interpreter.
"""

from __future__ import annotations

import builtins
import io
import json
import sys

import pandas as pd

from .validator import CodeValidationError, validate

_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "bytearray", "bytes", "dict", "enumerate",
    "filter", "float", "format", "frozenset", "int", "isinstance",
    "issubclass", "len", "list", "map", "max", "min", "next", "print",
    "range", "repr", "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "type", "zip",
    "True", "False", "None",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "StopIteration", "ZeroDivisionError", "RuntimeError", "ArithmeticError",
    "AttributeError", "NameError",
    # Needed internally for `import x` statements to work; direct source use
    # of the identifier '__import__' is separately blocked by validator.py.
    "__import__",
)

SAFE_BUILTINS = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES if hasattr(builtins, name)}


def _serialize(value: object) -> object:
    if isinstance(value, (pd.DataFrame, pd.Series)):
        if hasattr(value, "memory_usage") and value.memory_usage(deep=True).sum() > 1e8:
            value = value.head(100)
        return value.to_dict()
    if isinstance(value, dict):
        return value
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _write(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str)


def main() -> None:
    request_path, result_path = sys.argv[1], sys.argv[2]
    with open(request_path, "r", encoding="utf-8") as f:
        request = json.load(f)

    code = request["code"]
    file_path = request.get("file_path")
    result = {"success": False, "result": None, "stdout": "", "error_type": None, "error_message": None}

    try:
        validate(code)
    except CodeValidationError as e:
        result["error_type"] = "SECURITY_VIOLATION"
        result["error_message"] = str(e)
        _write(result_path, result)
        return

    exec_globals: dict = {"__builtins__": SAFE_BUILTINS, "pd": pd, "file_path": file_path}
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        exec(compile(code, "<user_code>", "exec"), exec_globals, exec_globals)
        value = exec_globals.get("result")
        if value is None:
            result["error_type"] = "NO_RESULT"
            result["error_message"] = "Code did not assign a 'result' variable."
        else:
            result["success"] = True
            result["result"] = _serialize(value)
    except Exception as e:  # noqa: BLE001 - worker boundary, must not crash unreported
        result["error_type"] = "EXECUTION_ERROR"
        result["error_message"] = str(e)
    finally:
        sys.stdout = old_stdout
        result["stdout"] = stdout_capture.getvalue()
        _write(result_path, result)


if __name__ == "__main__":
    main()
