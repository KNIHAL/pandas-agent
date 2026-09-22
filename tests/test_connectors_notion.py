"""Tests for connectors.notion_connector -- mocked against Notion's
documented REST shapes (no live workspace/integration token available).
Mocks requests.get/requests.post at the module level."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.notion_connector import NotionConnector
from connectors.errors import EntityNotFoundError

DB_ID = "db-123"

DATABASE_META = {
    "properties": {
        "Name": {"type": "title"},
        "Region": {"type": "select"},
        "Amount": {"type": "number"},
    }
}


def _page(name, region, amount):
    return {
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": name}]},
            "Region": {"type": "select", "select": {"name": region}},
            "Amount": {"type": "number", "number": amount},
        }
    }


def _resp(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    return NotionConnector("fake-token")


@patch("connectors.notion_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.notion_connector.requests.get")
def test_test_connection_false_on_401(mock_get, connector):
    mock_get.return_value = _resp(401)
    assert connector.test_connection() is False


@patch("connectors.notion_connector.requests.post")
def test_list_entities_paginates(mock_post, connector):
    mock_post.side_effect = [
        _resp(200, {"results": [{"id": "db-a"}], "has_more": True, "next_cursor": "c1"}),
        _resp(200, {"results": [{"id": "db-b"}], "has_more": False}),
    ]
    assert connector.list_entities() == ["db-a", "db-b"]
    assert mock_post.call_count == 2


@patch("connectors.notion_connector.requests.get")
def test_get_schema_returns_fields_and_types(mock_get, connector):
    mock_get.return_value = _resp(200, DATABASE_META)
    schema = connector.get_schema(DB_ID)
    assert schema["fields"] == ["Name", "Region", "Amount"]
    assert schema["field_types"]["Amount"] == "number"


@patch("connectors.notion_connector.requests.get")
def test_get_schema_unknown_database_raises(mock_get, connector):
    mock_get.return_value = _resp(404)
    with pytest.raises(EntityNotFoundError):
        connector.get_schema(DB_ID)


@patch("connectors.notion_connector.requests.post")
@patch("connectors.notion_connector.requests.get")
def test_fetch_extracts_property_values(mock_get, mock_post, connector):
    mock_get.return_value = _resp(200, DATABASE_META)
    mock_post.return_value = _resp(
        200, {"results": [_page("Order 1", "us", 10), _page("Order 2", "eu", 20)], "has_more": False}
    )
    df = connector.fetch(DB_ID)
    assert len(df) == 2
    assert df.iloc[0]["Name"] == "Order 1"
    assert df.iloc[0]["Region"] == "us"
    assert df.iloc[0]["Amount"] == 10


@patch("connectors.notion_connector.requests.post")
@patch("connectors.notion_connector.requests.get")
def test_fetch_respects_limit_across_pages(mock_get, mock_post, connector):
    mock_get.return_value = _resp(200, DATABASE_META)
    mock_post.side_effect = [
        _resp(200, {"results": [_page("A", "us", 1), _page("B", "us", 2)], "has_more": True, "next_cursor": "c1"}),
        _resp(200, {"results": [_page("C", "us", 3)], "has_more": False}),
    ]
    df = connector.fetch(DB_ID, limit=3)
    assert len(df) == 3


@patch("connectors.notion_connector.requests.post")
@patch("connectors.notion_connector.requests.get")
def test_fetch_applies_columns_selection(mock_get, mock_post, connector):
    mock_get.return_value = _resp(200, DATABASE_META)
    mock_post.return_value = _resp(200, {"results": [_page("A", "us", 1)], "has_more": False})
    df = connector.fetch(DB_ID, columns=["Name"])
    assert list(df.columns) == ["Name"]


@patch("connectors.notion_connector.requests.post")
@patch("connectors.notion_connector.requests.get")
def test_fetch_builds_typed_filter_for_select_property(mock_get, mock_post, connector):
    mock_get.return_value = _resp(200, DATABASE_META)
    mock_post.return_value = _resp(200, {"results": [], "has_more": False})
    connector.fetch(DB_ID, filters={"Region": "us"})
    sent_body = mock_post.call_args.kwargs["json"]
    assert sent_body["filter"] == {"property": "Region", "select": {"equals": "us"}}
