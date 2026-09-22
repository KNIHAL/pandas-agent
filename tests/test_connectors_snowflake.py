"""Tests for connectors.snowflake_connector -- mocked against
snowflake-connector-python's connection/cursor interface (no live
Snowflake account available; the free trial requires a card on file)."""

from unittest.mock import MagicMock, patch

import pytest

from connectors.snowflake_connector import SnowflakeConnector
from connectors.errors import EntityNotFoundError


@pytest.fixture
def connector():
    with patch("connectors.snowflake_connector.snowflake.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        conn = SnowflakeConnector("acct", "user", "pass", "wh", "DB1", schema="PUBLIC")
        conn._conn = mock_conn  # direct handle for assertions
        yield conn


def test_test_connection_true_when_query_succeeds(connector):
    connector._conn.cursor.return_value.execute.return_value = None
    assert connector.test_connection() is True


def test_test_connection_false_on_error(connector):
    connector._conn.cursor.return_value.execute.side_effect = Exception("no warehouse")
    assert connector.test_connection() is False


def test_list_entities_queries_information_schema(connector):
    cur = MagicMock()
    cur.fetchall.return_value = [("ORDERS",), ("CUSTOMERS",)]
    connector._conn.cursor.return_value = cur
    assert connector.list_entities() == ["ORDERS", "CUSTOMERS"]
    sent_sql = cur.execute.call_args.args[0]
    assert "information_schema.tables" in sent_sql
    assert cur.execute.call_args.args[1] == ("PUBLIC",)


def test_get_schema_returns_fields_and_types(connector):
    cur = MagicMock()
    cur.fetchall.return_value = [("ID", "NUMBER"), ("REGION", "TEXT")]
    connector._conn.cursor.return_value = cur
    schema = connector.get_schema("orders")
    assert schema["fields"] == ["ID", "REGION"]
    assert schema["field_types"]["REGION"] == "TEXT"


def test_get_schema_unknown_table_raises(connector):
    cur = MagicMock()
    cur.fetchall.return_value = []
    connector._conn.cursor.return_value = cur
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("nope")


def test_fetch_runs_select_and_returns_dataframe(connector):
    schema_cur = MagicMock()
    schema_cur.fetchall.return_value = [("ID", "NUMBER")]
    fetch_cur = MagicMock()
    fetch_cur.description = [("ID",)]
    fetch_cur.fetchall.return_value = [(1,), (2,)]
    connector._conn.cursor.side_effect = [schema_cur, fetch_cur]

    df = connector.fetch("orders")

    assert len(df) == 2
    sent_sql = fetch_cur.execute.call_args.args[0]
    assert 'FROM "DB1"."PUBLIC"."orders"' in sent_sql


def test_fetch_applies_columns_filters_limit(connector):
    schema_cur = MagicMock()
    schema_cur.fetchall.return_value = [("ID", "NUMBER"), ("REGION", "TEXT")]
    fetch_cur = MagicMock()
    fetch_cur.description = [("REGION",)]
    fetch_cur.fetchall.return_value = [("us",)]
    connector._conn.cursor.side_effect = [schema_cur, fetch_cur]

    df = connector.fetch("orders", columns=["region"], filters={"region": "us"}, limit=1)

    assert len(df) == 1
    sent_sql = fetch_cur.execute.call_args.args[0]
    sent_params = fetch_cur.execute.call_args.args[1]
    assert 'SELECT "region" FROM' in sent_sql
    assert 'WHERE "region" = %s' in sent_sql
    assert "LIMIT 1" in sent_sql
    assert sent_params == ["us"]
