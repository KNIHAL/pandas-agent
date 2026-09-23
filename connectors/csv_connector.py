"""CSV/file connector -- V1 first target per spec.md.

Scope: a directory of .csv files, each file is one entity. Whole-file reads
(no streaming) -- fine for V1's proof-of-pattern goal; revisit with chunked
reads if a real dataset stops fitting in memory.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import Connector
from .errors import EntityNotFoundError


class CSVConnector(Connector):
    name = "csv"

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)

    def test_connection(self) -> bool:
        return self._root.is_dir()

    def list_entities(self) -> list[str]:
        if not self._root.is_dir():
            return []
        return sorted(p.name for p in self._root.glob("*.csv"))

    def _resolve(self, entity: str) -> Path:
        path = self._root / entity
        if not path.is_file():
            raise EntityNotFoundError(f"No CSV file '{entity}' under {self._root}.")
        return path

    def get_schema(self, entity: str) -> dict:
        path = self._resolve(entity)
        df = pd.read_csv(path, nrows=100)
        return {
            "fields": list(df.columns),
            "field_types": {c: str(df[c].dtype) for c in df.columns},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        path = self._resolve(entity)
        df = pd.read_csv(path, usecols=columns)
        if filters:
            for col, val in filters.items():
                df = df[df[col] == val]
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)
