"""Tests for connectors.gateway_adapter -- all 12 tools wired into a real
ToolGateway, exercised via CSVConnector."""

import pandas as pd
import pytest

from connectors.csv_connector import CSVConnector
from connectors.gateway_adapter import make_connector_contracts
from connectors.registry import DatasetRegistry
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


@pytest.fixture
def gateway(tmp_path):
    pd.DataFrame(
        {"id": [1, 2, 3, 4], "amount": [10, None, 30, 30], "region": ["us", "eu", "us", "us"]}
    ).to_csv(tmp_path / "sales.csv", index=False)

    registry = DatasetRegistry()
    registry.register_connector(CSVConnector(tmp_path))

    gw = ToolGateway(granted_permissions={Permission.READ_DATA, Permission.ARTIFACT_WRITE})
    for contract in make_connector_contracts(registry):
        gw.register(contract)
    return gw, tmp_path


def test_query_data_via_gateway(gateway):
    gw, _ = gateway
    result = gw.invoke("query_data", {"source": "csv", "entity": "sales.csv", "limit": 2})
    assert result.success
    assert result.data.row_count == 2


def test_fetch_dataset_via_gateway(gateway):
    gw, _ = gateway
    result = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    assert result.success
    assert result.data.rows == 4


def test_release_dataset_via_gateway(gateway):
    gw, _ = gateway
    fetched = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    result = gw.invoke("release_dataset", {"dataset_id": fetched.data.dataset_id})
    assert result.success
    assert result.data.released is True


def test_materialize_dataset_via_gateway(gateway):
    gw, tmp_path = gateway
    fetched = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    out_path = str(tmp_path / "materialized" / "sales.parquet")
    result = gw.invoke("materialize_dataset", {"dataset_id": fetched.data.dataset_id, "path": out_path})
    assert result.success
    assert pd.read_parquet(result.data.path).shape[0] == 4


def test_profile_dataset_via_gateway(gateway):
    gw, _ = gateway
    fetched = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    result = gw.invoke("profile_dataset", {"dataset_id": fetched.data.dataset_id})
    assert result.success
    assert result.data.rows == 4


def test_check_missing_via_gateway(gateway):
    gw, _ = gateway
    fetched = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    result = gw.invoke("check_missing", {"dataset_id": fetched.data.dataset_id, "column": "amount"})
    assert result.success
    assert result.data.columns["amount"]["null_count"] == 1


def test_assess_data_quality_via_gateway(gateway):
    gw, _ = gateway
    fetched = gw.invoke("fetch_dataset", {"source": "csv", "entity": "sales.csv"})
    result = gw.invoke("assess_data_quality", {"dataset_id": fetched.data.dataset_id})
    assert result.success
    assert 0 <= result.data.score <= 100


def test_quality_tool_unknown_dataset_returns_execution_error(gateway):
    gw, _ = gateway
    result = gw.invoke("profile_dataset", {"dataset_id": "nope"})
    assert not result.success
    assert result.error.type == "EXECUTION_ERROR"


def test_connector_tools_denied_without_permission(tmp_path):
    pd.DataFrame({"id": [1]}).to_csv(tmp_path / "sales.csv", index=False)
    registry = DatasetRegistry()
    registry.register_connector(CSVConnector(tmp_path))
    gw = ToolGateway(granted_permissions=set())
    for contract in make_connector_contracts(registry):
        gw.register(contract)
    result = gw.invoke("query_data", {"source": "csv", "entity": "sales.csv"})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
