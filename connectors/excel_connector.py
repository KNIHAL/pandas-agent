"""Excel connector -- same directory-of-files pattern as CSVConnector.

An entity is "<file>.xlsx#<SheetName>" (or "<file>.xlsx" alone, which
defaults to the first sheet). Whole-sheet reads, no streaming -- same V1
scope note as CSVConnector.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import Connector
from .errors import EntityNotFoundError

_EXCEL_EXTS = (".xlsx", ".xls")


class ExcelConnector(Connector):
    name = "excel"

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)

    def test_connection(self) -> bool:
        return self._root.is_dir()

    def list_entities(self) -> list[str]:
        if not self._root.is_dir():
            return []
        entities: list[str] = []
        for path in sorted(self._root.iterdir()):
            if path.suffix.lower() not in _EXCEL_EXTS:
                continue
            try:
                with pd.ExcelFile(path) as xf:
                    for sheet in xf.sheet_names:
                        entities.append(f"{path.name}#{sheet}")
            except Exception:
                continue
        return entities

    def _resolve(self, entity: str) -> tuple[Path, str]:
        file_part, _, sheet_part = entity.partition("#")
        path = self._root / file_part
        if not path.is_file() or path.suffix.lower() not in _EXCEL_EXTS:
            raise EntityNotFoundError(f"No Excel file '{file_part}' under {self._root}.")
        with pd.ExcelFile(path) as xf:
            sheet = sheet_part or xf.sheet_names[0]
            if sheet not in xf.sheet_names:
                raise EntityNotFoundError(f"No sheet '{sheet}' in '{file_part}'.")
        return path, sheet

    def get_schema(self, entity: str) -> dict:
        path, sheet = self._resolve(entity)
        df = pd.read_excel(path, sheet_name=sheet, nrows=100)
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
        path, sheet = self._resolve(entity)
        df = pd.read_excel(path, sheet_name=sheet, usecols=columns)
        if filters:
            for col, val in filters.items():
                df = df[df[col] == val]
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)
