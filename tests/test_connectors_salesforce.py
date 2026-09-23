"""Tests for connectors.salesforce_connector -- mocked against
Salesforce's documented OAuth2/REST/SOQL response shapes (no live org
available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.salesforce_connector import SalesforceConnector
from connectors.errors import ConnectionFailedError, EntityNotFoundError


def _resp(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


AUTH_OK = _resp(200, {"access_token": "fake-token", "instance_url": "https://example.my.salesforce.com"})


@pytest.fixture
def connector():
    with patch("connectors.salesforce_connector.requests.post", return_value=AUTH_OK):
        yield SalesforceConnector("user", "pass", "token", "cid", "csecret")


@patch("connectors.salesforce_connector.requests.post")
def test_init_raises_connection_failed_on_bad_auth(mock_post):
    mock_post.return_value = _resp(400, {"error": "invalid_grant"})
    mock_post.return_value.raise_for_status.side_effect = Exception("HTTP 400")
    with pytest.raises(ConnectionFailedError):
        SalesforceConnector("user", "wrong", "token", "cid", "csecret")


@patch("connectors.salesforce_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.salesforce_connector.requests.get")
def test_list_entities_filters_queryable_only(mock_get, connector):
    mock_get.return_value = _resp(
        200, {"sobjects": [{"name": "Account", "queryable": True}, {"name": "Hidden", "queryable": False}]}
    )
    assert connector.list_entities() == ["Account"]


@patch("connectors.salesforce_connector.requests.get")
def test_get_schema_returns_fields_and_types(mock_get, connector):
    mock_get.return_value = _resp(
        200, {"fields": [{"name": "Id", "type": "id"}, {"name": "Name", "type": "string"}]}
    )
    schema = connector.get_schema("Account")
    assert schema["fields"] == ["Id", "Name"]
    assert schema["field_types"]["Name"] == "string"


@patch("connectors.salesforce_connector.requests.get")
def test_get_schema_unknown_sobject_raises(mock_get, connector):
    mock_get.return_value = _resp(404)
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("NoSuchObject")


@patch("connectors.salesforce_connector.requests.get")
def test_fetch_builds_soql_and_strips_attributes(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"fields": [{"name": "Id", "type": "id"}, {"name": "Name", "type": "string"}]}),
        _resp(200, {"records": [{"attributes": {"type": "Account"}, "Id": "001", "Name": "Acme"}], "done": True}),
    ]
    df = connector.fetch("Account")
    assert len(df) == 1
    assert "attributes" not in df.columns
    assert df.iloc[0]["Name"] == "Acme"
    query_call = mock_get.call_args_list[1]
    assert "SELECT Id, Name FROM Account" in query_call.kwargs["params"]["q"]


@patch("connectors.salesforce_connector.requests.get")
def test_fetch_applies_filters_and_limit_in_soql(mock_get, connector):
    mock_get.return_value = _resp(200, {"records": [], "done": True})
    connector.fetch("Account", columns=["Id"], filters={"Industry": "Tech"}, limit=5)
    soql = mock_get.call_args.kwargs["params"]["q"]
    assert "WHERE Industry = 'Tech'" in soql
    assert "LIMIT 5" in soql


@patch("connectors.salesforce_connector.requests.get")
def test_fetch_follows_next_records_url(mock_get, connector):
    mock_get.side_effect = [
        _resp(
            200,
            {
                "records": [{"attributes": {}, "Id": "001"}],
                "done": False,
                "nextRecordsUrl": "/services/data/v59.0/query/01g-2000",
            },
        ),
        _resp(200, {"records": [{"attributes": {}, "Id": "002"}], "done": True}),
    ]
    df = connector.fetch("Account", columns=["Id"])
    assert len(df) == 2
