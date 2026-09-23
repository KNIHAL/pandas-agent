"""Connector registration + in-memory dataset materialization.

Backs the four data-access tools: query_data (bounded preview, safe to hand
to the LLM), fetch_dataset (pulls a full result into memory, returns a
dataset_id handle -- never raw rows), materialize_dataset (persists a
fetched dataset to disk as an artifact), release_dataset (frees memory).
This is the "LLM never sees raw datasets directly" rule from agent-core's
philosophy, enforced here so every tool built on top of a materialized
dataset (data quality, investigation-engine) inherits it for free.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd

from .base import Connector
from .errors import DatasetNotFoundError, EntityNotFoundError


class DatasetHandle:
    def __init__(self, dataset_id: str, df: pd.DataFrame, *, source: str, entity: str) -> None:
        self.dataset_id = dataset_id
        self.df = df
        self.source = source
        self.entity = entity

    def summary(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "source": self.source,
            "entity": self.entity,
            "rows": len(self.df),
            "columns": list(self.df.columns),
        }


class DatasetRegistry:
    """Holds registered connectors and in-memory materialized datasets."""

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}
        self._datasets: dict[str, DatasetHandle] = {}

    # -- connectors -----------------------------------------------------

    def register_connector(self, connector: Connector) -> None:
        self._connectors[connector.name] = connector

    def get_connector(self, source: str) -> Connector:
        if source not in self._connectors:
            raise EntityNotFoundError(f"No connector registered for source '{source}'.")
        return self._connectors[source]

    def list_sources(self) -> list[str]:
        return sorted(self._connectors.keys())

    # -- data access ------------------------------------------------------

    def query(
        self,
        source: str,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        return self.get_connector(source).fetch(entity, columns=columns, limit=limit, filters=filters)

    def fetch_dataset(
        self,
        source: str,
        entity: str,
        *,
        columns: list[str] | None = None,
        filters: dict | None = None,
    ) -> DatasetHandle:
        df = self.get_connector(source).fetch(entity, columns=columns, filters=filters)
        dataset_id = uuid.uuid4().hex[:12]
        handle = DatasetHandle(dataset_id, df, source=source, entity=entity)
        self._datasets[dataset_id] = handle
        return handle

    def get_dataset(self, dataset_id: str) -> DatasetHandle:
        if dataset_id not in self._datasets:
            raise DatasetNotFoundError(f"No materialized dataset '{dataset_id}'. It may have been released.")
        return self._datasets[dataset_id]

    def release_dataset(self, dataset_id: str) -> bool:
        return self._datasets.pop(dataset_id, None) is not None

    def materialize_dataset(self, dataset_id: str, path: str | Path, *, fmt: str = "parquet") -> str:
        handle = self.get_dataset(dataset_id)
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "parquet":
            handle.df.to_parquet(out_path)
        elif fmt == "csv":
            handle.df.to_csv(out_path, index=False)
        else:
            raise ValueError(f"Unsupported export format '{fmt}'.")
        return str(out_path)
