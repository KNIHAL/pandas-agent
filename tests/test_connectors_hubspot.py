"""Tests for connectors.hubspot_connector -- mocked against HubSpot CRM
API v3's documented shapes (no live account available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.hubspot_connector import HubSpotConnector
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
    return HubSpotConnector("fake-token")


@patch("connectors.hubspot_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


def test_list_entities_returns_known_objects(connector):
    assert connector.list_entities() == ["companies", "contacts", "deals", "line_items", "products", "tickets"]


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("bogus")


@patch("connectors.hubspot_connector.requests.get")
def test_get_schema_returns_property_names_and_types(mock_get, connector):
    mock_get.return_value = _resp(200, {"results": [{"name": "email", "type": "string"}]})
    schema = connector.get_schema("contacts")
    assert schema["fields"] == ["email"]
    assert schema["field_types"]["email"] == "string"


@patch("connectors.hubspot_connector.requests.get")
def test_fetch_without_filters_uses_list_endpoint_and_flattens(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"results": [{"name": "email"}]}),  # _all_properties
        _resp(200, {"results": [{"id": "1", "properties": {"email": "a@x.com"}}], "paging": {}}),
    ]
    df = connector.fetch("contacts")
    assert len(df) == 1
    assert df.iloc[0]["email"] == "a@x.com"
    assert df.iloc[0]["id"] == "1"


@patch("connectors.hubspot_connector.requests.post")
def test_fetch_with_filters_uses_search_endpoint(mock_post, connector):
    mock_post.return_value = _resp(200, {"results": [{"id": "1", "properties": {"email": "a@x.com"}}], "paging": {}})
    df = connector.fetch("contacts", columns=["email"], filters={"email": "a@x.com"})
    assert len(df) == 1
    sent_body = mock_post.call_args.kwargs["json"]
    assert sent_body["filterGroups"][0]["filters"][0] == {"propertyName": "email", "operator": "EQ", "value": "a@x.com"}


@patch("connectors.hubspot_connector.requests.get")
def test_fetch_paginates_via_after_cursor(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"results": [{"id": "1", "properties": {}}], "paging": {"next": {"after": "c1"}}}),
        _resp(200, {"results": [{"id": "2", "properties": {}}], "paging": {}}),
    ]
    df = connector.fetch("contacts", columns=["id"])
    assert len(df) == 2
