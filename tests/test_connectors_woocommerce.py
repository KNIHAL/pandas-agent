"""Tests for connectors.woocommerce_connector -- mocked against
WooCommerce REST API v3's documented shapes (no live store available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.woocommerce_connector import WooCommerceConnector
from connectors.errors import EntityNotFoundError


def _resp(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else []
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    return WooCommerceConnector("https://shop.example.com", "ck_fake", "cs_fake")


@patch("connectors.woocommerce_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.woocommerce_connector.requests.get")
def test_test_connection_false_on_401(mock_get, connector):
    mock_get.return_value = _resp(401)
    assert connector.test_connection() is False


def test_list_entities_returns_known_resources(connector):
    assert connector.list_entities() == ["coupons", "customers", "orders", "products", "refunds"]


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("bogus")


def test_fetch_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.fetch("bogus")


@patch("connectors.woocommerce_connector.requests.get")
def test_get_schema_infers_fields_from_sample(mock_get, connector):
    mock_get.return_value = _resp(200, [{"id": 1, "name": "Widget", "price": "9.99"}])
    schema = connector.get_schema("products")
    assert schema["fields"] == ["id", "name", "price"]


@patch("connectors.woocommerce_connector.requests.get")
def test_fetch_paginates_until_short_page(mock_get, connector):
    full_page = [{"id": i} for i in range(100)]
    short_page = [{"id": 100}]
    mock_get.side_effect = [_resp(200, full_page), _resp(200, short_page)]
    df = connector.fetch("orders")
    assert len(df) == 101
    assert mock_get.call_count == 2


@patch("connectors.woocommerce_connector.requests.get")
def test_fetch_passes_filters_as_query_params(mock_get, connector):
    mock_get.return_value = _resp(200, [])
    connector.fetch("orders", filters={"status": "completed"})
    params = mock_get.call_args.kwargs["params"]
    assert params["status"] == "completed"


@patch("connectors.woocommerce_connector.requests.get")
def test_fetch_applies_limit_and_columns(mock_get, connector):
    mock_get.return_value = _resp(200, [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
    df = connector.fetch("products", columns=["name"], limit=1)
    assert list(df.columns) == ["name"]
    assert len(df) == 1
