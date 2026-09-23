"""Postgres connector -- V1 second target per spec.md.

SQLAlchemy-based, consistent with data_catalog/db.py's engine pattern.
Column/table identifiers are double-quoted rather than string-interpolated
from raw user text; values always go through bound parameters.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .base import Connector
from .errors import EntityNotFoundError


class PostgresConnector(Connector):
    name = "postgres"

    def __init__(self, connection_string: str, *, schema: str = "public") -> None:
        self._connection_string = connection_string
        self._schema = schema
        self._engine: Engine = create_engine(connection_string, future=True)

    def test_connection(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(inspect(self._engine).get_table_names(schema=self._schema))

    def _check_entity(self, entity: str) -> None:
        if entity not in inspect(self._engine).get_table_names(schema=self._schema):
            raise EntityNotFoundError(f"No table '{entity}' in schema '{self._schema}'.")

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        cols = inspect(self._engine).get_columns(entity, schema=self._schema)
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
        cols_sql = ", ".join(f'"{c}"' for c in columns) if columns else "*"
        query = f'SELECT {cols_sql} FROM "{self._schema}"."{entity}"'
        params: dict = {}
        if filters:
            clauses = []
            for i, (col, val) in enumerate(filters.items()):
                key = f"p{i}"
                clauses.append(f'"{col}" = :{key}')
                params[key] = val
            query += " WHERE " + " AND ".join(clauses)
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
