"""Tests for connectors.csv_connector."""

import pandas as pd
import pytest

from connectors.csv_connector import CSVConnector
from connectors.errors import EntityNotFoundError


@pytest.fixture
def csv_dir(tmp_path):
    pd.DataFrame({"id": [1, 2, 3], "region": ["us", "eu", "us"]}).to_csv(tmp_path / "orders.csv", index=False)
    pd.DataFrame({"id": [1, 2]}).to_csv(tmp_path / "customers.csv", index=False)
    return tmp_path


def test_test_connection_true_for_existing_dir(csv_dir):
    assert CSVConnector(csv_dir).test_connection() is True


def test_test_connection_false_for_missing_dir(tmp_path):
    assert CSVConnector(tmp_path / "nope").test_connection() is False


def test_list_entities_lists_csv_files(csv_dir):
    assert CSVConnector(csv_dir).list_entities() == ["customers.csv", "orders.csv"]


def test_get_schema_returns_fields_and_types(csv_dir):
    schema = CSVConnector(csv_dir).get_schema("orders.csv")
    assert schema["fields"] == ["id", "region"]
    assert "region" in schema["field_types"]


def test_get_schema_unknown_entity_raises(csv_dir):
    with pytest.raises(EntityNotFoundError):
        CSVConnector(csv_dir).get_schema("nope.csv")


def test_fetch_returns_all_rows_by_default(csv_dir):
    df = CSVConnector(csv_dir).fetch("orders.csv")
    assert len(df) == 3
    assert list(df.columns) == ["id", "region"]


def test_fetch_applies_columns_limit_filters(csv_dir):
    df = CSVConnector(csv_dir).fetch("orders.csv", columns=["region"], filters={"region": "us"}, limit=1)
    assert list(df.columns) == ["region"]
    assert len(df) == 1
    assert (df["region"] == "us").all()


def test_fetch_unknown_entity_raises(csv_dir):
    with pytest.raises(EntityNotFoundError):
        CSVConnector(csv_dir).fetch("nope.csv")
