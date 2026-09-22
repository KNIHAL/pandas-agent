"""Tests for connectors.registry -- DatasetRegistry backing the 4 data-access
tools, exercised with CSVConnector as the underlying source."""

import pandas as pd
import pytest

from connectors.csv_connector import CSVConnector
from connectors.errors import DatasetNotFoundError, EntityNotFoundError
from connectors.registry import DatasetRegistry


@pytest.fixture
def registry(tmp_path):
    pd.DataFrame({"id": [1, 2, 3], "amount": [10, 20, 30]}).to_csv(tmp_path / "sales.csv", index=False)
    reg = DatasetRegistry()
    reg.register_connector(CSVConnector(tmp_path))
    return reg


def test_list_sources(registry):
    assert registry.list_sources() == ["csv"]


def test_get_connector_unknown_source_raises(registry):
    with pytest.raises(EntityNotFoundError):
        registry.get_connector("postgres")


def test_query_returns_dataframe(registry):
    df = registry.query("csv", "sales.csv", limit=2)
    assert len(df) == 2


def test_fetch_dataset_returns_handle_and_registers_it(registry):
    handle = registry.fetch_dataset("csv", "sales.csv")
    assert handle.dataset_id
    assert len(handle.df) == 3
    assert registry.get_dataset(handle.dataset_id) is handle


def test_get_dataset_unknown_id_raises(registry):
    with pytest.raises(DatasetNotFoundError):
        registry.get_dataset("nope")


def test_release_dataset_frees_it(registry):
    handle = registry.fetch_dataset("csv", "sales.csv")
    assert registry.release_dataset(handle.dataset_id) is True
    with pytest.raises(DatasetNotFoundError):
        registry.get_dataset(handle.dataset_id)


def test_release_dataset_returns_false_when_already_gone(registry):
    assert registry.release_dataset("nope") is False


def test_materialize_dataset_writes_parquet(registry, tmp_path):
    handle = registry.fetch_dataset("csv", "sales.csv")
    out = registry.materialize_dataset(handle.dataset_id, tmp_path / "out" / "sales.parquet")
    written = pd.read_parquet(out)
    assert len(written) == 3


def test_materialize_dataset_writes_csv(registry, tmp_path):
    handle = registry.fetch_dataset("csv", "sales.csv")
    out = registry.materialize_dataset(handle.dataset_id, tmp_path / "sales_out.csv", fmt="csv")
    written = pd.read_csv(out)
    assert len(written) == 3


def test_materialize_dataset_unsupported_format_raises(registry, tmp_path):
    handle = registry.fetch_dataset("csv", "sales.csv")
    with pytest.raises(ValueError):
        registry.materialize_dataset(handle.dataset_id, tmp_path / "sales.xyz", fmt="xyz")
