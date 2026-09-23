"""Pydantic input/output schemas for the 6 investigation-engine
gateway-exposed tools.

compare_segments and drill_down take `data: list[dict]` (records) rather
than a dataset_id + live source fetch -- fetching real data by id is a
connectors/execution-backend integration this module doesn't own.
Callers pass already-fetched rows. See DECISIONS.md.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel


class CreateHypothesisInput(BaseModel):
    investigation_id: str
    statement: str


class CreateHypothesisOutput(BaseModel):
    hypothesis_id: str
    statement: str
    status: str


class TestHypothesisInput(BaseModel):
    investigation_id: str
    hypothesis_id: str
    description: str
    passed: Optional[bool] = None


class TestHypothesisOutput(BaseModel):
    test_id: str
    hypothesis_id: str
    hypothesis_status: str
    passed: Optional[bool] = None


class CompareSegmentsInput(BaseModel):
    investigation_id: str
    data: list[dict[str, Any]]
    segment_col: str
    metric_col: str
    segment_a: Any
    segment_b: Any
    agg: str = "sum"


class CompareSegmentsOutput(BaseModel):
    values: dict[str, float]
    diff: float
    change_a_vs_b: dict[str, float]


class DrillDownInput(BaseModel):
    investigation_id: str
    data: list[dict[str, Any]]
    group_cols: Union[str, list[str]]
    metric_col: str
    agg: str = "sum"
    filter_col: Optional[str] = None
    filter_op: Optional[str] = None
    filter_value: Any = None
    top_n: Optional[int] = None


class DrillDownOutput(BaseModel):
    rows: list[dict[str, Any]]


class EvaluateEvidenceInput(BaseModel):
    investigation_id: str
    description: str
    test_id: Optional[str] = None
    contribution_pct: Optional[float] = None


class EvaluateEvidenceOutput(BaseModel):
    evidence_id: str
    test_id: Optional[str] = None
    investigation_status: str


class VerifyFindingInput(BaseModel):
    investigation_id: str
    statement: str
    evidence_ids: list[str]
    limitations: Optional[list[str]] = None


class VerifyFindingOutput(BaseModel):
    finding_id: str
    statement: str
    evidence_ids: list[str]
    limitations: list[str]
