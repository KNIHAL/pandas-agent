"""Tests for tool_gateway.contracts — schema shape, defaults, validation."""

import pytest
from pydantic import BaseModel, ValidationError

from tool_gateway.contracts import (
    FailureBehavior,
    Permission,
    ToolContract,
    ToolLimits,
)


class DummyIn(BaseModel):
    x: int


class DummyOut(BaseModel):
    y: int


def dummy_handler(inp: DummyIn) -> DummyOut:
    return DummyOut(y=inp.x)


def test_contract_minimal_construction_has_expected_defaults():
    contract = ToolContract(
        name="dummy",
        purpose="Does dummy things.",
        input_schema=DummyIn,
        output_schema=DummyOut,
        permission=Permission.READ_DATA,
        handler=dummy_handler,
    )
    assert contract.name == "dummy"
    assert contract.timeout_seconds == 30.0
    assert contract.failure_behavior == FailureBehavior.RETURN_ERROR
    assert contract.source_requirements == []
    assert isinstance(contract.limits, ToolLimits)
    assert contract.limits.max_rows is None
    assert contract.limits.max_query_seconds is None
    assert contract.limits.max_output_bytes is None


def test_contract_missing_required_field_raises():
    with pytest.raises(ValidationError):
        ToolContract(
            purpose="Missing name.",
            input_schema=DummyIn,
            output_schema=DummyOut,
            permission=Permission.READ_DATA,
            handler=dummy_handler,
        )


def test_contract_rejects_invalid_permission_value():
    with pytest.raises(ValidationError):
        ToolContract(
            name="dummy",
            purpose="Bad permission.",
            input_schema=DummyIn,
            output_schema=DummyOut,
            permission="not_a_real_permission",
            handler=dummy_handler,
        )


def test_contract_accepts_custom_limits_and_failure_behavior():
    contract = ToolContract(
        name="dummy",
        purpose="Custom limits.",
        input_schema=DummyIn,
        output_schema=DummyOut,
        permission=Permission.WRITE_DATA,
        limits=ToolLimits(max_rows=100, max_query_seconds=2.5, max_output_bytes=1024),
        timeout_seconds=5.0,
        source_requirements=["duckdb"],
        failure_behavior=FailureBehavior.RAISE,
        handler=dummy_handler,
    )
    assert contract.limits.max_rows == 100
    assert contract.limits.max_query_seconds == 2.5
    assert contract.limits.max_output_bytes == 1024
    assert contract.timeout_seconds == 5.0
    assert contract.source_requirements == ["duckdb"]
    assert contract.failure_behavior == FailureBehavior.RAISE


def test_permission_enum_values_are_stable_strings():
    # These strings are used in audit logs / error messages — pin them.
    assert Permission.READ_DATA.value == "read_data"
    assert Permission.WRITE_DATA.value == "write_data"
    assert Permission.EXECUTE_CODE.value == "execute_code"
    assert Permission.NETWORK.value == "network"
    assert Permission.ARTIFACT_WRITE.value == "artifact_write"


def test_failure_behavior_enum_values_are_stable_strings():
    assert FailureBehavior.RAISE.value == "raise"
    assert FailureBehavior.RETURN_ERROR.value == "return_error"
    assert FailureBehavior.RETRY_ONCE.value == "retry_once"
