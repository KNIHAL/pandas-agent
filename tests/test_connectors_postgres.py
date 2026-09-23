"""Tests for connectors.postgres_connector -- live-tested against a
throwaway postgres:16-alpine Docker container (connectors-pg-test,
localhost:55432/testdb, table 'orders'), per the project's Docker-based
connector-testing convention. Skipped automatically if that container
isn't reachable (CI / a machine without Docker running)."""

import pandas as pd
import psycopg2
import pytest

from connectors.postgres_connector import PostgresConnector
from connectors.errors import EntityNotFoundError

CONN_STRING = "postgresql://postgres:test@localhost:55432/testdb"


def _pg_available() -> bool:
    try:
        psycopg2.connect(CONN_STRING, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_available(), reason="connectors-pg-test container not reachable")


@pytest.fixture
def connector():
    return PostgresConnector(CONN_STRING)


def test_test_connection_true_when_reachable(connector):
    assert connector.test_connection() is True


def test_test_connection_false_for_bad_connection_string():
    bad = PostgresConnector("postgresql://postgres:wrong@localhost:55432/testdb")
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
