"""Tests for connectors.ga4_connector -- mocked against the Analytics Data
API v1beta's documented REST shapes (no live GA4 property available)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.ga4_connector import GA4Connector
from connectors.errors import EntityNotFoundError


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
    with patch("connectors.ga4_connector.service_account.Credentials.from_service_account_file") as mock_creds:
        creds = MagicMock()
        creds.valid = True
        creds.token = "fake-access-token"
        mock_creds.return_value = creds
        yield GA4Connector("fake-key.json", "properties/123")


@patch("connectors.ga4_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.ga4_connector.requests.get")
def test_test_connection_false_on_403(mock_get, connector):
    mock_get.return_value = _resp(403)
    assert connector.test_connection() is False


def test_list_entities_returns_presets(connector):
    entities = connector.list_entities()
    assert "date|activeUsers,sessions" in entities


def test_get_schema_parses_dims_and_metrics(connector):
    schema = connector.get_schema("date,country|activeUsers,sessions")
    assert schema["fields"] == ["date", "country", "activeUsers", "sessions"]
    assert schema["field_types"]["date"] == "STRING"
    assert schema["field_types"]["sessions"] == "NUMBER"


def test_get_schema_invalid_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("not-a-valid-spec")


@patch("connectors.ga4_connector.requests.post")
def test_fetch_parses_rows_into_dataframe(mock_post, connector):
    mock_post.return_value = _resp(
        200,
        {
            "rows": [
                {"dimensionValues": [{"value": "us"}], "metricValues": [{"value": "42"}]},
                {"dimensionValues": [{"value": "in"}], "metricValues": [{"value": "17"}]},
            ]
        },
    )
    df = connector.fetch("country|activeUsers")
    assert len(df) == 2
    assert list(df.columns) == ["country", "activeUsers"]
    assert df.iloc[0]["country"] == "us"
    assert df.iloc[0]["activeUsers"] == "42"


@patch("connectors.ga4_connector.requests.post")
def test_fetch_uses_default_date_range(mock_post, connector):
    mock_post.return_value = _resp(200, {"rows": []})
    connector.fetch("date|activeUsers")
    body = mock_post.call_args.kwargs["json"]
    assert body["dateRanges"] == [{"startDate": "30daysAgo", "endDate": "today"}]


@patch("connectors.ga4_connector.requests.post")
def test_fetch_applies_custom_date_range_and_dimension_filter(mock_post, connector):
    mock_post.return_value = _resp(200, {"rows": []})
    connector.fetch("country|activeUsers", filters={"start_date": "7daysAgo", "end_date": "today", "country": "us"})
    body = mock_post.call_args.kwargs["json"]
    assert body["dateRanges"] == [{"startDate": "7daysAgo", "endDate": "today"}]
    assert body["dimensionFilter"] == {
        "filter": {"fieldName": "country", "stringFilter": {"matchType": "EXACT", "value": "us"}}
    }


@patch("connectors.ga4_connector.requests.post")
def test_fetch_applies_columns_selection(mock_post, connector):
    mock_post.return_value = _resp(
        200, {"rows": [{"dimensionValues": [{"value": "us"}], "metricValues": [{"value": "42"}]}]}
    )
    df = connector.fetch("country|activeUsers", columns=["activeUsers"])
    assert list(df.columns) == ["activeUsers"]
