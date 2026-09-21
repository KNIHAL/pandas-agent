"""Tests for execution_backend.validator — AST-based static pre-check."""

import pytest

from execution_backend.validator import CodeValidationError, validate


def test_allowed_imports_pass():
    validate("import pandas as pd\nimport numpy as np\nresult = 1")


def test_allowed_submodule_import_passes():
    validate("import matplotlib.pyplot as plt\nresult = 1")


def test_syntax_error_raises_validation_error():
    with pytest.raises(CodeValidationError):
        validate("def f(:\n    pass")


@pytest.mark.parametrize("code", [
    "import os\nresult = 1",
    "import subprocess\nresult = 1",
    "import socket\nresult = 1",
    "from os import path\nresult = 1",
])
def test_disallowed_imports_raise(code):
    with pytest.raises(CodeValidationError):
        validate(code)


@pytest.mark.parametrize("code", [
    "result = eval('1+1')",
    "result = __import__('os')",
    "result = open('/etc/passwd')",
    "result = exec('1')",
    "g = globals()\nresult = 1",
])
def test_blocked_builtin_names_raise(code):
    with pytest.raises(CodeValidationError):
        validate(code)


def test_dunder_attribute_access_raises():
    with pytest.raises(CodeValidationError):
        validate("result = (1).__class__.__bases__")


def test_ordinary_pandas_code_passes():
    validate(
        "import pandas as pd\n"
        "df = pd.read_csv(file_path)\n"
        "result = df.sum()\n"
    )
