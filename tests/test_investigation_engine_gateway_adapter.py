"""Tests for investigation_engine.gateway_adapter -- the 6 tools wired
into a real ToolGateway."""
import pytest

from investigation_engine.gateway_adapter import make_investigation_engine_contracts
from investigation_engine.loop_controller import InvestigationLoopController
from investigation_engine.persistence import InMemoryInvestigationStore
from investigation_engine.state import Bounds
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


@pytest.fixture
def store():
    return InMemoryInvestigationStore()


@pytest.fixture
def investigation_id(store):
    controller = InvestigationLoopController(store=store)
    state = controller.start("Why did August revenue drop?", bounds=Bounds(min_evidence_items=1))
    return state.id


@pytest.fixture
def gateway(store):
    gw = ToolGateway(granted_permissions={Permission.READ_DATA, Permission.WRITE_DATA})
    for contract in make_investigation_engine_contracts(store):
        gw.register(contract)
    return gw


@pytest.fixture
def sales_data():
    return [
        {"product": "A", "region": "east", "revenue": 100},
        {"product": "A", "region": "west", "revenue": 50},
        {"product": "B", "region": "east", "revenue": 200},
        {"product": "B", "region": "west", "revenue": 30},
        {"product": "C", "region": "east", "revenue": 20},
    ]


def test_create_hypothesis_via_gateway(gateway, investigation_id):
    result = gateway.invoke("create_hypothesis", {
        "investigation_id": investigation_id, "statement": "Product B stockout in west",
    })
    assert result.success
    assert result.data.statement == "Product B stockout in west"
    assert result.data.status == "proposed"


def test_create_hypothesis_unknown_investigation_fails(gateway):
    result = gateway.invoke("create_hypothesis", {
        "investigation_id": "does-not-exist", "statement": "x",
    })
    assert not result.success


def test_test_hypothesis_via_gateway(gateway, investigation_id):
    created = gateway.invoke("create_hypothesis", {
        "investigation_id": investigation_id, "statement": "H1",
    })
    result = gateway.invoke("test_hypothesis", {
        "investigation_id": investigation_id,
        "hypothesis_id": created.data.hypothesis_id,
        "description": "checked inventory data",
        "passed": True,
    })
    assert result.success
    assert result.data.hypothesis_status == "supported"


def test_compare_segments_via_gateway(gateway, investigation_id, sales_data):
    result = gateway.invoke("compare_segments", {
        "investigation_id": investigation_id,
        "data": sales_data,
        "segment_col": "product",
        "metric_col": "revenue",
        "segment_a": "B",
        "segment_b": "C",
    })
    assert result.success
    assert result.data.diff == 230 - 20


def test_drill_down_via_gateway(gateway, investigation_id, sales_data):
    result = gateway.invoke("drill_down", {
        "investigation_id": investigation_id,
        "data": sales_data,
        "group_cols": "product",
        "metric_col": "revenue",
        "filter_col": "region",
        "filter_op": "==",
        "filter_value": "east",
        "top_n": 1,
    })
    assert result.success
    assert result.data.rows[0]["product"] == "B"


def test_evaluate_evidence_via_gateway(gateway, investigation_id):
    result = gateway.invoke("evaluate_evidence", {
        "investigation_id": investigation_id,
        "description": "sufficient evidence found",
    })
    assert result.success
    assert result.data.investigation_status == "enough_evidence"


def test_verify_finding_via_gateway(gateway, investigation_id):
    ev = gateway.invoke("evaluate_evidence", {
        "investigation_id": investigation_id, "description": "evidence text",
    })
    result = gateway.invoke("verify_finding", {
        "investigation_id": investigation_id,
        "statement": "Revenue drop driven by product B stockout in west",
        "evidence_ids": [ev.data.evidence_id],
    })
    assert result.success
    assert result.data.finding_id


def test_verify_finding_unknown_evidence_fails(gateway, investigation_id):
    result = gateway.invoke("verify_finding", {
        "investigation_id": investigation_id, "statement": "x", "evidence_ids": ["nope"],
    })
    assert not result.success


def test_tools_denied_without_permission(store, investigation_id):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_investigation_engine_contracts(store):
        gw.register(contract)
    result = gw.invoke("create_hypothesis", {"investigation_id": investigation_id, "statement": "x"})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
