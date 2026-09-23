"""Tests for connectors.stripe_connector -- mocked against Stripe's
documented REST shapes (no account available; Stripe doesn't currently
allow Indian self-signup)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.stripe_connector import StripeConnector
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
    return StripeConnector("sk_test_fake")


@patch("connectors.stripe_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.stripe_connector.requests.get")
def test_test_connection_false_on_401(mock_get, connector):
    mock_get.return_value = _resp(401)
    assert connector.test_connection() is False


def test_list_entities_returns_known_resources(connector):
    entities = connector.list_entities()
    assert "customers" in entities
    assert "charges" in entities
    assert entities == sorted(entities)


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("bogus_resource")


def test_fetch_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.fetch("bogus_resource")


@patch("connectors.stripe_connector.requests.get")
def test_get_schema_infers_fields_from_sample(mock_get, connector):
    mock_get.return_value = _resp(200, {"data": [{"id": "cus_1", "email": "a@x.com", "balance": 0}]})
    schema = connector.get_schema("customers")
    assert schema["fields"] == ["id", "email", "balance"]
    assert schema["field_types"]["balance"] == "int"


@patch("connectors.stripe_connector.requests.get")
def test_fetch_paginates_via_starting_after(mock_get, connector):
    mock_get.side_effect = [
        _resp(200, {"data": [{"id": "cus_1"}, {"id": "cus_2"}], "has_more": True}),
        _resp(200, {"data": [{"id": "cus_3"}], "has_more": False}),
    ]
    df = connector.fetch("customers")
    assert len(df) == 3
    second_call_params = mock_get.call_args_list[1].kwargs["params"]
    assert second_call_params["starting_after"] == "cus_2"


@patch("connectors.stripe_connector.requests.get")
def test_fetch_passes_filters_as_query_params(mock_get, connector):
    mock_get.return_value = _resp(200, {"data": [], "has_more": False})
    connector.fetch("customers", filters={"email": "a@x.com"})
    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params["email"] == "a@x.com"


@patch("connectors.stripe_connector.requests.get")
def test_fetch_applies_limit_and_columns(mock_get, connector):
    mock_get.return_value = _resp(
        200, {"data": [{"id": "cus_1", "email": "a@x.com"}, {"id": "cus_2", "email": "b@x.com"}], "has_more": False}
    )
    df = connector.fetch("customers", columns=["email"], limit=1)
    assert list(df.columns) == ["email"]
    assert len(df) == 1
