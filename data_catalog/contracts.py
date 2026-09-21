"""Pydantic I/O schemas for the four data-catalog tools."""

from __future__ import annotations

from pydantic import BaseModel


class CatalogEntrySummary(BaseModel):
    source: str
    entity: str
    table: str | None = None
    authority: bool
    metrics: list[str]


class CatalogEntryDetail(CatalogEntrySummary):
    fields: list[str]
    dimensions: list[str]
    date_fields: list[str]
    freshness: dict
    relationships: list[dict]
    permissions: dict
    lineage: str | None = None


class ListSourcesInput(BaseModel):
    pass


class ListSourcesOutput(BaseModel):
    sources: list[str]


class InspectSourceInput(BaseModel):
    source: str


class InspectSourceOutput(BaseModel):
    source: str
    entries: list[CatalogEntrySummary]


class InspectSchemaInput(BaseModel):
    source: str
    entity: str


class InspectSchemaOutput(BaseModel):
    entries: list[CatalogEntryDetail]


class FindDataInput(BaseModel):
    query: str


class FindDataOutput(BaseModel):
    matches: list[CatalogEntrySummary]
