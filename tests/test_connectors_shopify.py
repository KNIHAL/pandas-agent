"""Tests for connectors.shopify_connector -- mocked against Shopify's
documented Admin REST API shapes (no live dev store available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.shopify_connector import ShopifyConnector, _parse_next_link
from connectors.errors import EntityNotFoundError


def _resp(status_code=200, json_data=None, link=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = {"Link": link} if link else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    return ShopifyConnector("test-shop", "fake-token")


def test_parse_next_link_extracts_next_url():
    header = '<https://x.myshopify.com/admin/api/2024-01/products.json?page_info=abc>; rel="next"'
    assert _parse_next_link(header) == "https://x.myshopify.com/admin/api/2024-01/products.json?page_info=abc"


def test_parse_next_link_returns_none_when_no_next():
    header = '<https://x.myshopify.com/admin/api/2024-01/products.json?page_info=abc>; rel="previous"'
    assert _parse_next_link(header) is None


def test_parse_next_link_handles_empty():
    assert _parse_next_link(None) is None
    assert _parse_next_link("") is None


@patch("connectors.shopify_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.shopify_connector.requests.get")
def test_test_connection_false_on_401(mock_get, connector):
    mock_get.return_value = _resp(401)
    assert connector.test_connection() is False


def test_list_entities_returns_known_resources(connector):
    assert connector.list_entities() == ["collections", "customers", "inventory_items", "orders", "products"]


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("bogus")


def test_fetch_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.fetch("bogus")


@patch("connectors.shopify_connector.requests.get")
def test_get_schema_infers_fields_from_sample(mock_get, connector):
    mock_get.return_value = _resp(200, {"products": [{"id": 1, "title": "Widget"}]})
    schema = connector.get_schema("products")
    assert schema["fields"] == ["id", "title"]


@patch("connectors.shopify_connector.requests.get")
def test_fetch_follows_link_header_pagination(mock_get, connector):
    next_url = "https://test-shop.myshopify.com/admin/api/2024-01/products.json?page_info=abc"
    mock_get.side_effect = [
        _resp(200, {"products": [{"id": 1}]}, link=f'<{next_url}>; rel="next"'),
        _resp(200, {"products": [{"id": 2}]}),
    ]
    df = connector.fetch("products")
    assert len(df) == 2
    assert mock_get.call_args_list[1].args[0] == next_url


@patch("connectors.shopify_connector.requests.get")
def test_fetch_passes_filters_as_query_params(mock_get, connector):
    mock_get.return_value = _resp(200, {"orders": []})
    connector.fetch("orders", filters={"status": "any"})
    params = mock_get.call_args.kwargs["params"]
    assert params["status"] == "any"


@patch("connectors.shopify_connector.requests.get")
def test_fetch_applies_limit_and_columns(mock_get, connector):
    mock_get.return_value = _resp(200, {"products": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]})
    df = connector.fetch("products", columns=["title"], limit=1)
    assert list(df.columns) == ["title"]
    assert len(df) == 1
