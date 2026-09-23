"""Tests for connectors.excel_connector."""

import pandas as pd
import pytest

from connectors.excel_connector import ExcelConnector
from connectors.errors import EntityNotFoundError


@pytest.fixture
def excel_dir(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"id": [1, 2, 3], "region": ["us", "eu", "us"]}).to_excel(
            writer, sheet_name="orders", index=False
        )
        pd.DataFrame({"id": [1, 2]}).to_excel(writer, sheet_name="customers", index=False)
    return tmp_path


def test_test_connection_true_for_existing_dir(excel_dir):
    assert ExcelConnector(excel_dir).test_connection() is True


def test_test_connection_false_for_missing_dir(tmp_path):
    assert ExcelConnector(tmp_path / "nope").test_connection() is False


def test_list_entities_lists_one_per_sheet(excel_dir):
    assert ExcelConnector(excel_dir).list_entities() == ["book.xlsx#orders", "book.xlsx#customers"]


def test_get_schema_returns_fields_and_types(excel_dir):
    schema = ExcelConnector(excel_dir).get_schema("book.xlsx#orders")
    assert schema["fields"] == ["id", "region"]


def test_get_schema_defaults_to_first_sheet_without_hash(excel_dir):
    schema = ExcelConnector(excel_dir).get_schema("book.xlsx")
    assert schema["fields"] == ["id", "region"]  # "orders" is the first sheet


def test_get_schema_unknown_file_raises(excel_dir):
    with pytest.raises(EntityNotFoundError):
        ExcelConnector(excel_dir).get_schema("nope.xlsx#orders")


def test_get_schema_unknown_sheet_raises(excel_dir):
    with pytest.raises(EntityNotFoundError):
        ExcelConnector(excel_dir).get_schema("book.xlsx#nope")


def test_fetch_returns_all_rows_by_default(excel_dir):
    df = ExcelConnector(excel_dir).fetch("book.xlsx#orders")
    assert len(df) == 3
    assert list(df.columns) == ["id", "region"]


def test_fetch_applies_columns_limit_filters(excel_dir):
    df = ExcelConnector(excel_dir).fetch(
        "book.xlsx#orders", columns=["region"], filters={"region": "us"}, limit=1
    )
    assert list(df.columns) == ["region"]
    assert len(df) == 1
    assert (df["region"] == "us").all()


def test_fetch_unknown_entity_raises(excel_dir):
    with pytest.raises(EntityNotFoundError):
        ExcelConnector(excel_dir).fetch("nope.xlsx#orders")
