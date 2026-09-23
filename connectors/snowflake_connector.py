"""Snowflake connector -- official snowflake-connector-python driver,
auth via account/user/password + warehouse/database/schema (role
optional). Uses INFORMATION_SCHEMA for table/column listing rather than
SHOW TABLES/SHOW COLUMNS, since INFORMATION_SCHEMA has a stable, queryable
shape instead of a free-form result set.

No live Snowflake account was available to test against (the free trial
needs a card on file per Snowflake's own signup, not yet set up), so
this is verified against a mocked connection/cursor -- see
tests/test_connectors_snowflake.py. Swap in real credentials and it
should work unchanged; re-verify against a live trial account before
relying on it.
"""

from __future__ import annotations

import pandas as pd
import snowflake.connector

from .base import Connector
from .errors import EntityNotFoundError


class SnowflakeConnector(Connector):
    name = "snowflake"

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        warehouse: str,
        database: str,
        schema: str = "PUBLIC",
        role: str | None = None,
    ) -> None:
        self._conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role,
        )
        self._database = database
        self._schema = schema

    def test_connection(self) -> bool:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
            (self._schema,),
        )
        return [r[0] for r in cur.fetchall()]

    def get_schema(self, entity: str) -> dict:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (self._schema, entity.upper()),
        )
        rows = cur.fetchall()
        if not rows:
            raise EntityNotFoundError(f"No Snowflake table '{entity}' in schema '{self._schema}'.")
        return {"fields": [r[0] for r in rows], "field_types": {r[0]: r[1] for r in rows}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        self.get_schema(entity)  # validates existence
        cols_sql = ", ".join(f'"{c}"' for c in columns) if columns else "*"
        query = f'SELECT {cols_sql} FROM "{self._database}"."{self._schema}"."{entity}"'
        params: list = []
        if filters:
            clauses = [f'"{col}" = %s' for col in filters]
            params = list(filters.values())
            query += " WHERE " + " AND ".join(clauses)
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        cur = self._conn.cursor()
        cur.execute(query, params)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)
