"""Wraps investigation_engine's 6 tools as tool_gateway ToolContracts.

The analytical-engine functions (aggregation/statistical/time-series/
business) and the loop controller are internal -- only these 6 tools
from spec.md are agent-facing, same split as data_catalog's adapter.
"""
from __future__ import annotations

import pandas as pd
from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from investigation_engine.contracts import (
    CompareSegmentsInput,
    CompareSegmentsOutput,
    CreateHypothesisInput,
    CreateHypothesisOutput,
    DrillDownInput,
    DrillDownOutput,
    EvaluateEvidenceInput,
    EvaluateEvidenceOutput,
    TestHypothesisInput,
    TestHypothesisOutput,
    VerifyFindingInput,
    VerifyFindingOutput,
)
from investigation_engine.loop_controller import InvestigationLoopController
from investigation_engine.persistence import InvestigationStore
from investigation_engine import tools as _tools


class InvestigationNotFoundError(Exception):
    pass


def make_investigation_engine_contracts(
    store: InvestigationStore, timeout_seconds: float = 15.0
) -> list[ToolContract]:
    """Build all 6 investigation-engine ToolContracts for a given store."""

    controller = InvestigationLoopController(store=store)

    def _load(investigation_id: str):
        state = controller.load(investigation_id)
        if state is None:
            raise InvestigationNotFoundError(f"No investigation with id {investigation_id}")
        return state

    def create_hypothesis(inp: CreateHypothesisInput) -> CreateHypothesisOutput:
        state = _load(inp.investigation_id)
        hyp = _tools.create_hypothesis(controller, state, inp.statement)
        return CreateHypothesisOutput(hypothesis_id=hyp.id, statement=hyp.statement, status=hyp.status.value)

    def test_hypothesis(inp: TestHypothesisInput) -> TestHypothesisOutput:
        state = _load(inp.investigation_id)
        test = _tools.test_hypothesis(controller, state, inp.hypothesis_id, inp.description, inp.passed)
        hyp = next(h for h in state.hypotheses if h.id == inp.hypothesis_id)
        return TestHypothesisOutput(
            test_id=test.id, hypothesis_id=inp.hypothesis_id,
            hypothesis_status=hyp.status.value, passed=test.passed,
        )

    def compare_segments(inp: CompareSegmentsInput) -> CompareSegmentsOutput:
        state = _load(inp.investigation_id)
        df = pd.DataFrame(inp.data)
        result = _tools.compare_segments(
            controller, state, df, inp.segment_col, inp.metric_col,
            inp.segment_a, inp.segment_b, agg=inp.agg,
        )
        values = {str(k): float(v) for k, v in result[inp.segment_col].items()}
        return CompareSegmentsOutput(values=values, diff=result["diff"], change_a_vs_b=result["change_a_vs_b"])

    def drill_down(inp: DrillDownInput) -> DrillDownOutput:
        state = _load(inp.investigation_id)
        df = pd.DataFrame(inp.data)
        rows = _tools.drill_down(
            controller, state, df, inp.group_cols, inp.metric_col, agg=inp.agg,
            filter_col=inp.filter_col, filter_op=inp.filter_op, filter_value=inp.filter_value,
            top_n=inp.top_n,
        )
        return DrillDownOutput(rows=rows)

    def evaluate_evidence(inp: EvaluateEvidenceInput) -> EvaluateEvidenceOutput:
        state = _load(inp.investigation_id)
        ev = _tools.evaluate_evidence(
            controller, state, inp.description, test_id=inp.test_id, contribution_pct=inp.contribution_pct,
        )
        return EvaluateEvidenceOutput(evidence_id=ev.id, test_id=ev.test_id, investigation_status=state.status.value)

    def verify_finding(inp: VerifyFindingInput) -> VerifyFindingOutput:
        state = _load(inp.investigation_id)
        finding = _tools.verify_finding(controller, state, inp.statement, inp.evidence_ids, inp.limitations)
        return VerifyFindingOutput(
            finding_id=finding.id, statement=finding.statement,
            evidence_ids=finding.evidence_ids, limitations=finding.limitations,
        )

    return [
        ToolContract(
            name="create_hypothesis",
            purpose="Propose a candidate explanation for the question under investigation.",
            input_schema=CreateHypothesisInput,
            output_schema=CreateHypothesisOutput,
            permission=Permission.WRITE_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=create_hypothesis,
        ),
        ToolContract(
            name="test_hypothesis",
            purpose="Record a test run against a hypothesis and resolve its status.",
            input_schema=TestHypothesisInput,
            output_schema=TestHypothesisOutput,
            permission=Permission.WRITE_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=test_hypothesis,
        ),
        ToolContract(
            name="compare_segments",
            purpose="Head-to-head comparison of two segment values on one metric.",
            input_schema=CompareSegmentsInput,
            output_schema=CompareSegmentsOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=compare_segments,
        ),
        ToolContract(
            name="drill_down",
            purpose="Filter and group/aggregate a metric to narrow in on a candidate driver.",
            input_schema=DrillDownInput,
            output_schema=DrillDownOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=drill_down,
        ),
        ToolContract(
            name="evaluate_evidence",
            purpose="Record a piece of evidence and check whether enough has been gathered to stop.",
            input_schema=EvaluateEvidenceInput,
            output_schema=EvaluateEvidenceOutput,
            permission=Permission.WRITE_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=evaluate_evidence,
        ),
        ToolContract(
            name="verify_finding",
            purpose="Record a finding grounded in specific, already-gathered evidence items.",
            input_schema=VerifyFindingInput,
            output_schema=VerifyFindingOutput,
            permission=Permission.WRITE_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=verify_finding,
        ),
    ]
