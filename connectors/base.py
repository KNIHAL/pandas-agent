"""Abstract connector interface every data-source connector must implement.

Kept deliberately narrow: prove the source is reachable, list what's there,
describe an entity's schema, and pull rows into a DataFrame. Materialization,
quality checks, and catalog registration live in registry.py/quality.py so
adding a new source (Snowflake, Salesforce, ...) later never touches those
layers -- only a new subclass of Connector.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Connector(ABC):
    """Base interface for all data-source connectors."""

    name: str  # e.g. "csv", "postgres" -- set by each subclass

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the source is reachable, False otherwise. Never raises."""

    @abstractmethod
    def list_entities(self) -> list[str]:
        """List queryable entities (tables/files) this connector exposes."""

    @abstractmethod
    def get_schema(self, entity: str) -> dict:
        """Return {"fields": [...], "field_types": {name: type_str}} for an entity."""

    @abstractmethod
    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        """Pull rows from an entity into a DataFrame.

        filters is a simple {column: exact_value} equality map -- V1 scope
        only, per spec.md. Richer filter expressions can extend this later
        without changing the interface shape.
        """
