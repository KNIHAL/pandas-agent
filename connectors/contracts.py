"""Pydantic I/O schemas for the 4 data-access + 8 data-quality tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# -- data access ----------------------------------------------------------


class QueryDataInput(BaseModel):
    source: str
    entity: str
    columns: list[str] | None = None
    filters: dict[str, Any] | None = None
    limit: int = 50


class QueryDataOutput(BaseModel):
    rows: list[dict[str, Any]]
    row_count: int


class FetchDatasetInput(BaseModel):
    source: str
    entity: str
    columns: list[str] | None = None
    filters: dict[str, Any] | None = None


class FetchDatasetOutput(BaseModel):
    dataset_id: str
    source: str
    entity: str
    rows: int
    columns: list[str]


class MaterializeDatasetInput(BaseModel):
    dataset_id: str
    path: str
    format: str = "parquet"


class MaterializeDatasetOutput(BaseModel):
    path: str


class ReleaseDatasetInput(BaseModel):
    dataset_id: str


class ReleaseDatasetOutput(BaseModel):
    released: bool


# -- data quality -----------------------------------------------------------


class DatasetIdInput(BaseModel):
    dataset_id: str


class ProfileDatasetOutput(BaseModel):
    rows: int
    columns: list[dict[str, Any]]


class CheckMissingInput(BaseModel):
    dataset_id: str
    column: str | None = None


class CheckMissingOutput(BaseModel):
    columns: dict[str, dict[str, float]]


class CheckDuplicatesInput(BaseModel):
    dataset_id: str
    subset: list[str] | None = None


class CheckDuplicatesOutput(BaseModel):
    duplicate_count: int
    duplicate_pct: float
    sample_indices: list[int]


class CheckInvalidValuesInput(BaseModel):
    dataset_id: str
    column: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[Any] | None = None


class CheckInvalidValuesOutput(BaseModel):
    invalid_count: int
    invalid_pct: float
    sample_values: list[Any]


class CheckFormatConsistencyInput(BaseModel):
    dataset_id: str
    column: str


class CheckFormatConsistencyOutput(BaseModel):
    dominant_pattern: str | None
    consistency_pct: float
    pattern_counts: dict[str, int]


class CheckDateCoverageInput(BaseModel):
    dataset_id: str
    column: str


class CheckDateCoverageOutput(BaseModel):
    min_date: str | None
    max_date: str | None
    unparseable_count: int
    missing_days: int


class CheckSchemaInput(BaseModel):
    dataset_id: str
    expected_schema: dict[str, str]


class CheckSchemaOutput(BaseModel):
    missing_columns: list[str]
    extra_columns: list[str]
    type_mismatches: list[dict[str, str]]


class AssessDataQualityOutput(BaseModel):
    score: float
    avg_null_pct: float
    duplicate_pct: float
    flags: list[str]
