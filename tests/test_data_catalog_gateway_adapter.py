"""Tests for data_catalog.gateway_adapter — the 4 tools wired into a real
ToolGateway."""

import pytest

from data_catalog.db import make_engine, make_session_factory
from data_catalog.gateway_adapter import make_data_catalog_contracts
from data_catalog.repository import CatalogRepository
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


@pytest.fixture
def gateway():
    engine = make_engine(":memory:")
    repo = CatalogRepository(make_session_factory(engine))
    repo.upsert_entry(
        source="stripe", entity="payments", fields=["id", "amount"],
        metrics=["revenue"], authority=True,
    )
    repo.upsert_entry(source="shopify", entity="orders", fields=["id", "total"])

    gw = ToolGateway(granted_permissions={Permission.READ_DATA})
    for contract in make_data_catalog_contracts(repo):
        gw.register(contract)
    return gw


def test_list_sources_via_gateway(gateway):
    result = gateway.invoke("list_sources", {})
    assert result.success
    assert result.data.sources == ["shopify", "stripe"]


def test_inspect_source_via_gateway(gateway):
    result = gateway.invoke("inspect_source", {"source": "stripe"})
    assert result.success
    assert result.data.entries[0].entity == "payments"


def test_inspect_source_unknown_returns_empty(gateway):
    result = gateway.invoke("inspect_source", {"source": "nope"})
    assert result.success
    assert result.data.entries == []


def test_inspect_schema_via_gateway(gateway):
    result = gateway.invoke("inspect_schema", {"source": "stripe", "entity": "payments"})
    assert result.success
    assert result.data.entries[0].fields == ["id", "amount"]
    assert result.data.entries[0].authority is True


def test_find_data_via_gateway(gateway):
    result = gateway.invoke("find_data", {"query": "revenue"})
    assert result.success
    assert result.data.matches[0].source == "stripe"


def test_data_catalog_tools_denied_without_permission():
    engine = make_engine(":memory:")
    repo = CatalogRepository(make_session_factory(engine))
    gw = ToolGateway(granted_permissions=set())
    for contract in make_data_catalog_contracts(repo):
        gw.register(contract)
    result = gw.invoke("list_sources", {})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
