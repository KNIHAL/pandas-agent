"""Tests for connectors.teams_connector -- mocked against Microsoft
Graph's documented OAuth2/REST response shapes (no live tenant
available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.teams_connector import TeamsConnector
from connectors.errors import ConnectionFailedError, EntityNotFoundError


def _resp(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


AUTH_OK = _resp(200, {"access_token": "fake-token"})


@pytest.fixture
def connector():
    with patch("connectors.teams_connector.requests.post", return_value=AUTH_OK):
        yield TeamsConnector("tenant-1", "client-1", "secret-1")


@patch("connectors.teams_connector.requests.post")
def test_init_raises_connection_failed_on_bad_auth(mock_post):
    mock_post.return_value = _resp(400)
    with pytest.raises(ConnectionFailedError):
        TeamsConnector("tenant-1", "client-1", "wrong")


@patch("connectors.teams_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.teams_connector.requests.get")
def test_list_entities_combines_teams_and_channels(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"value": [{"id": "team1"}]}),
        _resp(200, {"value": [{"id": "chan1"}, {"id": "chan2"}]}),
    ]
    assert connector.list_entities() == ["team1/chan1", "team1/chan2"]


def test_get_schema_invalid_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("not-valid")


def test_get_schema_returns_fixed_message_fields(connector):
    schema = connector.get_schema("team1/chan1")
    assert schema["fields"] == ["id", "from", "body", "created_datetime"]


@patch("connectors.teams_connector.requests.get")
def test_fetch_extracts_message_fields(mock_get, connector):
    mock_get.return_value = _resp(
        200,
        {
            "value": [
                {
                    "id": "m1",
                    "from": {"user": {"displayName": "Kumar"}},
                    "body": {"content": "hi"},
                    "createdDateTime": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )
    df = connector.fetch("team1/chan1")
    assert len(df) == 1
    assert df.iloc[0]["from"] == "Kumar"
    assert df.iloc[0]["body"] == "hi"


@patch("connectors.teams_connector.requests.get")
def test_fetch_follows_odata_next_link(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"value": [{"id": "m1"}], "@odata.nextLink": "https://graph.microsoft.com/v1.0/next"}),
        _resp(200, {"value": [{"id": "m2"}]}),
    ]
    df = connector.fetch("team1/chan1")
    assert len(df) == 2


@patch("connectors.teams_connector.requests.get")
def test_fetch_applies_filters_and_columns(mock_get, connector):
    mock_get.return_value = _resp(
        200,
        {
            "value": [
                {"id": "m1", "from": {"user": {"displayName": "Kumar"}}, "body": {"content": "hi"}},
                {"id": "m2", "from": {"user": {"displayName": "Alex"}}, "body": {"content": "hey"}},
            ]
        },
    )
    df = connector.fetch("team1/chan1", columns=["from", "body"], filters={"from": "Alex"})
    assert list(df.columns) == ["from", "body"]
    assert len(df) == 1
    assert df.iloc[0]["body"] == "hey"
