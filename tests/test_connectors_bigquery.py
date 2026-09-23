"""Tests for connectors.bigquery_connector -- mocked against
google.cloud.bigquery.Client (no live GCP project available; billing
account was detached and sandbox mode not yet re-enabled)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from connectors.bigquery_connector import BigQueryConnector
from connectors.errors import EntityNotFoundError


class _FakeField:
    def __init__(self, name, field_type):
        self.name = name
        self.field_type = field_type


class _FakeTable:
    def __init__(self, table_id, schema=None):
        self.table_id = table_id
        self.schema = schema or []


@pytest.fixture
def connector():
    with patch("connectors.bigquery_connector.service_account.Credentials.from_service_account_file"):
        with patch("connectors.bigquery_connector.bigquery.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            conn = BigQueryConnector("fake-key.json", "proj-1", "dataset_1")
            conn._client = mock_client  # keep a direct handle for assertions
            yield conn


def test_test_connection_true_when_dataset_reachable(connector):
    connector._client.get_dataset.return_value = MagicMock()
    assert connector.test_connection() is True


def test_test_connection_false_on_error(connector):
    connector._client.get_dataset.side_effect = Exception("not found")
    assert connector.test_connection() is False


def test_list_entities_returns_sorted_table_ids(connector):
    connector._client.list_tables.return_value = [_FakeTable("orders"), _FakeTable("customers")]
    assert connector.list_entities() == ["customers", "orders"]


def test_get_schema_returns_fields_and_types(connector):
    connector._client.get_table.return_value = _FakeTable(
        "orders", schema=[_FakeField("id", "INTEGER"), _FakeField("region", "STRING")]
    )
    schema = connector.get_schema("orders")
    assert schema["fields"] == ["id", "region"]
    assert schema["field_types"]["region"] == "STRING"


def test_get_schema_unknown_table_raises(connector):
    connector._client.get_table.side_effect = Exception("404")
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("nope")


def test_fetch_runs_query_and_returns_dataframe(connector):
    connector._client.get_table.return_value = _FakeTable("orders")
    fake_job = MagicMock()
    fake_job.to_dataframe.return_value = pd.DataFrame({"id": [1, 2], "region": ["us", "eu"]})
    connector._client.query.return_value = fake_job

    df = connector.fetch("orders")

    assert len(df) == 2
    sent_query = connector._client.query.call_args.args[0]
    assert "FROM `proj-1.dataset_1.orders`" in sent_query


def test_fetch_applies_columns_and_limit_in_sql(connector):
    connector._client.get_table.return_value = _FakeTable("orders")
    fake_job = MagicMock()
    fake_job.to_dataframe.return_value = pd.DataFrame({"region": ["us"]})
    connector._client.query.return_value = fake_job

    connector.fetch("orders", columns=["region"], limit=5)

    sent_query = connector._client.query.call_args.args[0]
    assert "SELECT `region` FROM" in sent_query
    assert "LIMIT 5" in sent_query


def test_fetch_builds_parameterized_filter(connector):
    connector._client.get_table.return_value = _FakeTable("orders")
    fake_job = MagicMock()
    fake_job.to_dataframe.return_value = pd.DataFrame({"id": [1]})
    connector._client.query.return_value = fake_job

    connector.fetch("orders", filters={"region": "us"})

    sent_query = connector._client.query.call_args.args[0]
    job_config = connector._client.query.call_args.kwargs["job_config"]
    assert "WHERE `region` = @p0" in sent_query
    assert job_config.query_parameters[0].name == "p0"
