"""Tests for connectors.mixpanel_connector -- mocked against Mixpanel's
documented Query/Export API shapes (no live project available)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from connectors.mixpanel_connector import MixpanelConnector
from connectors.errors import EntityNotFoundError


def _resp(status_code=200, json_data=None, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text if text is not None else ""
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    return MixpanelConnector("svc-user", "svc-secret", "proj-1")


@patch("connectors.mixpanel_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.mixpanel_connector.requests.get")
def test_test_connection_false_on_401(mock_get, connector):
    mock_get.return_value = _resp(401)
    assert connector.test_connection() is False


@patch("connectors.mixpanel_connector.requests.get")
def test_list_entities_returns_sorted_event_names(mock_get, connector):
    mock_get.return_value = _resp(200, ["Purchase", "Login"])
    assert connector.list_entities() == ["Login", "Purchase"]


def _jsonl(*events):
    return "\n".join(json.dumps(e) for e in events)


@patch("connectors.mixpanel_connector.requests.get")
def test_fetch_parses_jsonl_and_flattens_properties(mock_get, connector):
    mock_get.return_value = _resp(
        200,
        text=_jsonl(
            {"event": "Purchase", "properties": {"time": 100, "distinct_id": "u1", "amount": 20, "region": "us"}},
            {"event": "Purchase", "properties": {"time": 101, "distinct_id": "u2", "amount": 30, "region": "eu"}},
        ),
    )
    df = connector.fetch("Purchase")
    assert len(df) == 2
    assert set(df.columns) == {"event", "time", "distinct_id", "amount", "region"}
    assert df.iloc[0]["amount"] == 20


@patch("connectors.mixpanel_connector.requests.get")
def test_fetch_unknown_event_raises(mock_get, connector):
    mock_get.return_value = _resp(404)
    with pytest.raises(EntityNotFoundError):
        connector.fetch("NoSuchEvent")


@patch("connectors.mixpanel_connector.requests.get")
def test_fetch_uses_default_7_day_range(mock_get, connector):
    mock_get.return_value = _resp(200, text="")
    connector.fetch("Purchase")
    params = mock_get.call_args.kwargs["params"]
    assert "from_date" in params and "to_date" in params


@patch("connectors.mixpanel_connector.requests.get")
def test_fetch_applies_custom_range_filters_and_columns(mock_get, connector):
    mock_get.return_value = _resp(
        200,
        text=_jsonl(
            {"event": "Purchase", "properties": {"time": 100, "distinct_id": "u1", "region": "us"}},
            {"event": "Purchase", "properties": {"time": 101, "distinct_id": "u2", "region": "eu"}},
        ),
    )
    df = connector.fetch(
        "Purchase",
        columns=["region"],
        filters={"start_date": "2026-01-01", "end_date": "2026-01-07", "region": "us"},
    )
    params = mock_get.call_args.kwargs["params"]
    assert params["from_date"] == "2026-01-01"
    assert params["to_date"] == "2026-01-07"
    assert list(df.columns) == ["region"]
    assert len(df) == 1
