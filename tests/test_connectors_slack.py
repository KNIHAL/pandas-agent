"""Tests for connectors.slack_connector -- mocked against Slack's documented
REST shapes (no live workspace/bot token available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.slack_connector import SlackConnector
from connectors.errors import EntityNotFoundError


def _resp(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


@pytest.fixture
def connector():
    return SlackConnector("fake-bot-token")


@patch("connectors.slack_connector.requests.post")
def test_test_connection_true_on_ok(mock_post, connector):
    mock_post.return_value = _resp({"ok": True})
    assert connector.test_connection() is True


@patch("connectors.slack_connector.requests.post")
def test_test_connection_false_on_error(mock_post, connector):
    mock_post.return_value = _resp({"ok": False, "error": "invalid_auth"})
    assert connector.test_connection() is False


@patch("connectors.slack_connector.requests.get")
def test_list_entities_paginates(mock_get, connector):
    mock_get.side_effect = [
        _resp({"ok": True, "channels": [{"id": "C1", "name": "general"}], "response_metadata": {"next_cursor": "c1"}}),
        _resp({"ok": True, "channels": [{"id": "C2", "name": "random"}], "response_metadata": {"next_cursor": ""}}),
    ]
    assert connector.list_entities() == ["general", "random"]


@patch("connectors.slack_connector.requests.get")
def test_get_schema_returns_fixed_message_fields(mock_get, connector):
    mock_get.return_value = _resp(
        {"ok": True, "channels": [{"id": "C1", "name": "general"}], "response_metadata": {}}
    )
    schema = connector.get_schema("general")
    assert schema["fields"] == ["ts", "user", "text", "type"]


@patch("connectors.slack_connector.requests.get")
def test_get_schema_unknown_channel_raises(mock_get, connector):
    mock_get.return_value = _resp({"ok": True, "channels": [], "response_metadata": {}})
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("nope")


@patch("connectors.slack_connector.requests.get")
def test_fetch_by_channel_name_resolves_id_then_fetches(mock_get, connector):
    mock_get.side_effect = [
        _resp({"ok": True, "channels": [{"id": "C1", "name": "general"}], "response_metadata": {}}),
        _resp(
            {
                "ok": True,
                "messages": [
                    {"ts": "1.1", "user": "U1", "text": "hi", "type": "message"},
                    {"ts": "1.2", "user": "U2", "text": "hey", "type": "message"},
                ],
                "has_more": False,
            }
        ),
    ]
    df = connector.fetch("general")
    assert len(df) == 2
    assert df.iloc[0]["text"] == "hi"


def test_fetch_accepts_raw_channel_id_without_lookup():
    connector = SlackConnector("fake-bot-token")
    with patch("connectors.slack_connector.requests.get") as mock_get:
        mock_get.return_value = _resp(
            {"ok": True, "messages": [{"ts": "1.1", "user": "U1", "text": "hi", "type": "message"}], "has_more": False}
        )
        df = connector.fetch("C0ABCDEF12")
        assert mock_get.call_count == 1  # no conversations.list lookup needed
        assert len(df) == 1


@patch("connectors.slack_connector.requests.get")
def test_fetch_applies_filters_and_columns(mock_get, connector):
    mock_get.side_effect = [
        _resp({"ok": True, "channels": [{"id": "C1", "name": "general"}], "response_metadata": {}}),
        _resp(
            {
                "ok": True,
                "messages": [
                    {"ts": "1.1", "user": "U1", "text": "hi", "type": "message"},
                    {"ts": "1.2", "user": "U2", "text": "hey", "type": "message"},
                ],
                "has_more": False,
            }
        ),
    ]
    df = connector.fetch("general", columns=["user", "text"], filters={"user": "U2"})
    assert list(df.columns) == ["user", "text"]
    assert len(df) == 1
    assert df.iloc[0]["text"] == "hey"
