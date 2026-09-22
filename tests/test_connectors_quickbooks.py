"""Tests for connectors.quickbooks_connector -- mocked against Intuit's
documented QuickBooks Online REST/query response shapes (no live sandbox
available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.quickbooks_connector import QuickBooksConnector
from connectors.errors import EntityNotFoundError


def _resp(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    return QuickBooksConnector("fake-token", "12345")


@patch("connectors.quickbooks_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


def test_list_entities_returns_known_objects(connector):
    assert connector.list_entities() == ["Account", "Bill", "Customer", "Invoice", "Item", "Payment", "Vendor"]


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("Bogus")


def test_fetch_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.fetch("Bogus")


@patch("connectors.quickbooks_connector.requests.get")
def test_get_schema_infers_from_sample(mock_get, connector):
    mock_get.return_value = _resp(200, {"QueryResponse": {"Customer": [{"Id": "1", "DisplayName": "Acme"}]}})
    schema = connector.get_schema("Customer")
    assert schema["fields"] == ["Id", "DisplayName"]


@patch("connectors.quickbooks_connector.requests.get")
def test_fetch_builds_query_with_where_and_maxresults(mock_get, connector):
    mock_get.return_value = _resp(200, {"QueryResponse": {"Customer": [{"Id": "1"}]}})
    df = connector.fetch("Customer", columns=["Id"], filters={"DisplayName": "Acme"}, limit=5)
    assert len(df) == 1
    soql = mock_get.call_args.kwargs["params"]["query"]
    assert "SELECT Id FROM Customer" in soql
    assert "WHERE DisplayName = 'Acme'" in soql
    assert "MAXRESULTS 5" in soql


@patch("connectors.quickbooks_connector.requests.get")
def test_fetch_defaults_maxresults_to_1000(mock_get, connector):
    mock_get.return_value = _resp(200, {"QueryResponse": {"Customer": []}})
    connector.fetch("Customer")
    soql = mock_get.call_args.kwargs["params"]["query"]
    assert "MAXRESULTS 1000" in soql
