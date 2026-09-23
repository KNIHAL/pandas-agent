"""Tests for connectors.mysql_connector -- live-tested against a throwaway
mysql:8 Docker container (connectors-mysql-test, localhost:53306/testdb,
table 'orders'). Skipped automatically if that container isn't reachable."""

import pandas as pd
import pymysql
import pytest

from connectors.mysql_connector import MySQLConnector
from connectors.errors import EntityNotFoundError

CONN_STRING = "mysql+pymysql://root:test@localhost:53306/testdb"


def _mysql_available() -> bool:
    try:
        pymysql.connect(host="localhost", port=53306, user="root", password="test", database="testdb", connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _mysql_available(), reason="connectors-mysql-test container not reachable")


@pytest.fixture
def connector():
    return MySQLConnector(CONN_STRING)


def test_test_connection_true_when_reachable(connector):
    assert connector.test_connection() is True


def test_test_connection_false_for_bad_connection_string():
    bad = MySQLConnector("mysql+pymysql://root:wrong@localhost:53306/testdb")
    assert bad.test_connection() is False


def test_list_entities_includes_orders(connector):
    assert "orders" in connector.list_entities()


def test_get_schema_returns_fields_and_types(connector):
    schema = connector.get_schema("orders")
    assert set(schema["fields"]) == {"id", "region", "amount"}


def test_get_schema_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("nope")


def test_fetch_returns_all_rows_by_default(connector):
    df = connector.fetch("orders")
    assert len(df) == 3
    assert set(df.columns) == {"id", "region", "amount"}


def test_fetch_applies_columns_filters_limit(connector):
    df = connector.fetch("orders", columns=["region", "amount"], filters={"region": "us"}, limit=1)
    assert list(df.columns) == ["region", "amount"]
    assert len(df) == 1
    assert (df["region"] == "us").all()


def test_fetch_unknown_entity_raises(connector):
    with pytest.raises(EntityNotFoundError):
        connector.fetch("nope")
