"""Domain errors for connectors."""

from __future__ import annotations


class ConnectorError(Exception):
    """Base class for all connector-layer errors."""


class ConnectionFailedError(ConnectorError):
    pass


class EntityNotFoundError(ConnectorError):
    pass


class DatasetNotFoundError(ConnectorError):
    """Raised when a dataset_id has no materialized handle in the registry
    (never fetched, or already released)."""
