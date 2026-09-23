"""The 6 investigation-engine tools.

Each tool takes the loop controller + current InvestigationState (plus
a pandas DataFrame for the ones that touch data) and returns a small
structured result -- never raw rows, per spec. Every call mutates and
persists state so the chain is always resumable.

Tool-gateway registration is a separate, later step (see
gateway_adapter.py once tool-gateway's ToolContract shape is
confirmed) -- these are plain, directly-callable/testable functions.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from investigation_engine.analytics.business import compare_segments as _compare_segments
from investigation_engine.analytics.core import filter_rows, group_by
from investigation_engine.loop_controller import InvestigationLoopController
from investigation_engine.state import (
    Evidence,
    Finding,
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    Observation,
    Test,
    _new_id,
)


class NotFoundError(Exception):
    """Raised when a referenced hypothesis/test/evidence id doesn't exist."""


def _find(items, item_id: str, kind: str):
    for item in items:
        if item.id == item_id:
            return item
    raise NotFoundError(f"{kind} not found: {item_id}")


def create_hypothesis(
    controller: InvestigationLoopController,
    state: InvestigationState,
    statement: str,
) -> Hypothesis:
    """Propose a candidate explanation for the question under
    investigation (spec step: hypothesis generation from decomposed
    candidate drivers)."""
    hyp = Hypothesis(id=_new_id("hyp"), statement=statement)
    state.hypotheses.append(hyp)
    controller.save(state)
    return hyp


def test_hypothesis(
    controller: InvestigationLoopController,
    state: InvestigationState,
    hypothesis_id: str,
    description: str,
    passed: Optional[bool] = None,
) -> Test:
    """Record a test run against a hypothesis and update the hypothesis's
    status accordingly. `passed=None` means the test is still pending
    (status moves to TESTING); True/False resolves it."""
    hyp = _find(state.hypotheses, hypothesis_id, "hypothesis")

    test = Test(id=_new_id("tst"), hypothesis_id=hypothesis_id, description=description, passed=passed)
    state.tests.append(test)

    if passed is None:
        hyp.status = HypothesisStatus.TESTING
    elif passed:
        hyp.status = HypothesisStatus.SUPPORTED
    else:
        hyp.status = HypothesisStatus.REJECTED

    controller.save(state)
    return test


def compare_segments(
    controller: InvestigationLoopController,
    state: InvestigationState,
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    segment_a: Any,
    segment_b: Any,
    agg: str = "sum",
) -> dict:
    """Head-to-head segment comparison, recorded as an Observation so the
    chain stays reconstructable."""
    result = _compare_segments(df, segment_col, metric_col, segment_a, segment_b, agg=agg)
    obs = Observation(
        id=_new_id("obs"),
        query_id=None,
        description=f"compare_segments: {segment_col} {segment_a} vs {segment_b} on {metric_col}",
        data=result,
    )
    state.observations.append(obs)
    controller.save(state)
    return result


def drill_down(
    controller: InvestigationLoopController,
    state: InvestigationState,
    df: pd.DataFrame,
    group_cols,
    metric_col: str,
    agg: str = "sum",
    filter_col: Optional[str] = None,
    filter_op: Optional[str] = None,
    filter_value: Any = None,
    top_n: Optional[int] = None,
) -> list[dict]:
    """Narrow into a metric by optional filter then group/aggregate.
    Returns a small list of grouped rows (never the raw table), recorded
    as an Observation."""
    working = df
    if filter_col is not None:
        working = filter_rows(working, filter_col, filter_op, filter_value)

    grouped = group_by(working, group_cols, metric_col, func=agg)
    if top_n is not None:
        grouped = grouped.head(top_n)
    result = grouped.to_dict(orient="records")

    obs = Observation(
        id=_new_id("obs"),
        query_id=None,
        description=f"drill_down: group={group_cols} metric={metric_col} filter={filter_col}",
        data={"rows": result},
    )
    state.observations.append(obs)
    controller.save(state)
    return result


def evaluate_evidence(
    controller: InvestigationLoopController,
    state: InvestigationState,
    description: str,
    test_id: Optional[str] = None,
    contribution_pct: Optional[float] = None,
) -> Evidence:
    """Record a piece of evidence, optionally linked to a test, then check
    whether the loop has gathered enough evidence to stop (per bounds)."""
    if test_id is not None:
        _find(state.tests, test_id, "test")

    ev = Evidence(
        id=_new_id("evd"),
        test_id=test_id,
        description=description,
        contribution_pct=contribution_pct,
    )
    state.evidence.append(ev)
    controller.save(state)
    controller.check_evidence_sufficiency(state)
    return ev


def verify_finding(
    controller: InvestigationLoopController,
    state: InvestigationState,
    statement: str,
    evidence_ids: list[str],
    limitations: Optional[list[str]] = None,
) -> Finding:
    """Record a finding grounded in specific evidence items. Every
    evidence_id must already exist on the investigation, so a finding
    can never cite evidence that was never gathered."""
    for eid in evidence_ids:
        _find(state.evidence, eid, "evidence")

    finding = Finding(
        id=_new_id("fnd"),
        statement=statement,
        evidence_ids=list(evidence_ids),
        limitations=list(limitations or []),
    )
    state.findings.append(finding)
    controller.save(state)
    return finding
