"""Tests for data_catalog.repository — CRUD, search, and authority resolution."""

import pytest

from data_catalog.db import make_engine, make_session_factory
from data_catalog.errors import AuthorityConflictError, EntryNotFoundError
from data_catalog.repository import CatalogRepository


@pytest.fixture
def repo():
    engine = make_engine(":memory:")
    return CatalogRepository(make_session_factory(engine))


def test_upsert_then_list_sources(repo):
    repo.upsert_entry(source="stripe", entity="payments", metrics=["revenue"])
    repo.upsert_entry(source="shopify", entity="orders", metrics=["revenue"])
    assert repo.list_sources() == ["shopify", "stripe"]


def test_upsert_is_idempotent_on_source_entity_table(repo):
    repo.upsert_entry(source="stripe", entity="payments", fields=["id"])
    repo.upsert_entry(source="stripe", entity="payments", fields=["id", "amount"])
    entries = repo.inspect_source("stripe")
    assert len(entries) == 1
    assert repo.inspect_schema("stripe", "payments")[0]["fields"] == ["id", "amount"]


def test_inspect_source_raises_when_unknown(repo):
    with pytest.raises(EntryNotFoundError):
        repo.inspect_source("nonexistent")


def test_inspect_schema_returns_full_detail(repo):
    repo.upsert_entry(
        source="stripe", entity="payments", table_name="payments_raw",
        fields=["id", "amount"], metrics=["revenue"], dimensions=["currency"],
        date_fields=["created_at"], authority=True,
        freshness={"refresh_interval_minutes": 60},
        relationships=[{"entity": "customers", "via": "customer_id"}],
        permissions={"roles": ["finance"]}, lineage="raw webhook ingest",
    )
    detail = repo.inspect_schema("stripe", "payments")[0]
    assert detail["fields"] == ["id", "amount"]
    assert detail["authority"] is True
    assert detail["lineage"] == "raw webhook ingest"


def test_find_data_matches_across_fields(repo):
    repo.upsert_entry(source="stripe", entity="payments", fields=["amount"], metrics=["revenue"])
    repo.upsert_entry(source="shopify", entity="orders", fields=["total"], dimensions=["region"])

    assert {m["source"] for m in repo.find_data("revenue")} == {"stripe"}
    assert {m["source"] for m in repo.find_data("region")} == {"shopify"}
    assert {m["source"] for m in repo.find_data("nope")} == set()


def test_authority_resolution_picks_flagged_entry(repo):
    repo.upsert_entry(source="stripe", entity="payments", metrics=["revenue"], authority=True)
    result = repo.resolve_authority("revenue")
    assert result["source"] == "stripe"


def test_authority_resolution_returns_none_when_unset(repo):
    repo.upsert_entry(source="stripe", entity="payments", metrics=["revenue"], authority=False)
    assert repo.resolve_authority("revenue") is None


def test_conflicting_authority_claim_raises(repo):
    repo.upsert_entry(source="stripe", entity="payments", metrics=["revenue"], authority=True)
    with pytest.raises(AuthorityConflictError):
        repo.upsert_entry(source="shopify", entity="orders", metrics=["revenue"], authority=True)


def test_conflicting_authority_claim_can_be_forced(repo):
    repo.upsert_entry(source="stripe", entity="payments", metrics=["revenue"], authority=True)
    repo.upsert_entry(
        source="shopify", entity="orders", metrics=["revenue"], authority=True, force_authority=True
    )
    assert repo.resolve_authority("revenue")["source"] == "shopify"
