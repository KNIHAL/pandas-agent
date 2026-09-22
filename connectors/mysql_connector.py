"""MySQL connector -- same SQLAlchemy pattern as PostgresConnector.

Uses PyMySQL as the driver (pure-Python, no system MySQL client needed).
Connection string format: "mysql+pymysql://user:pass@host:port/dbname".
Unlike Postgres, MySQL has no separate schema concept -- the database in
the connection string is the whole namespace, so there's no `schema` param.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .base import Connector
from .errors import EntityNotFoundError


class MySQLConnector(Connector):
    name = "mysql"

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._engine: Engine = create_engine(connection_string, future=True)

    def test_connection(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(inspect(self._engine).get_table_names())

    def _check_entity(self, entity: str) -> None:
        if entity not in inspect(self._engine).get_table_names():
            raise EntityNotFoundError(f"No table '{entity}'.")

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        cols = inspect(self._engine).get_columns(entity)
        return {
            "fields": [c["name"] for c in cols],
            "field_types": {c["name"]: str(c["type"]) for c in cols},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        self._check_entity(entity)
        cols_sql = ", ".join(f"`{c}`" for c in columns) if columns else "*"
        query = f"SELECT {cols_sql} FROM `{entity}`"
        params: dict = {}
        if filters:
            clauses = []
            for i, (col, val) in enumerate(filters.items()):
                key = f"p{i}"
                clauses.append(f"`{col}` = :{key}")
                params[key] = val
            query += " WHERE " + " AND ".join(clauses)
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
