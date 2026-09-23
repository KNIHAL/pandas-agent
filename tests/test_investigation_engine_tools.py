import pandas as pd
import pytest

from investigation_engine.loop_controller import InvestigationLoopController
from investigation_engine.persistence import InMemoryInvestigationStore
from investigation_engine.state import Bounds, HypothesisStatus
from investigation_engine.tools import (
    NotFoundError,
    compare_segments,
    create_hypothesis,
    drill_down,
    evaluate_evidence,
    test_hypothesis as run_hypothesis_test,
    verify_finding,
)


@pytest.fixture
def controller():
    return InvestigationLoopController(store=InMemoryInvestigationStore())


@pytest.fixture
def state(controller):
    return controller.start("Why did August revenue drop?", bounds=Bounds(min_evidence_items=1))


@pytest.fixture
def sales_df():
    return pd.DataFrame(
        {
            "product": ["A", "A", "B", "B", "C"],
            "region": ["east", "west", "east", "west", "east"],
            "revenue": [100, 50, 200, 30, 20],
        }
    )


def test_create_hypothesis_appends_and_persists(controller, state):
    hyp = create_hypothesis(controller, state, "Product B stockout in west region")
    assert hyp in state.hypotheses
    reloaded = controller.load(state.id)
    assert reloaded.hypotheses[0].statement == "Product B stockout in west region"


def test_test_hypothesis_supported_updates_status(controller, state):
    hyp = create_hypothesis(controller, state, "H1")
    run_hypothesis_test(controller, state, hyp.id, "checked stock levels", passed=True)
    assert hyp.status == HypothesisStatus.SUPPORTED


def test_test_hypothesis_rejected_updates_status(controller, state):
    hyp = create_hypothesis(controller, state, "H1")
    run_hypothesis_test(controller, state, hyp.id, "checked stock levels", passed=False)
    assert hyp.status == HypothesisStatus.REJECTED


def test_test_hypothesis_pending_sets_testing(controller, state):
    hyp = create_hypothesis(controller, state, "H1")
    run_hypothesis_test(controller, state, hyp.id, "still checking", passed=None)
    assert hyp.status == HypothesisStatus.TESTING


def test_test_hypothesis_unknown_id_raises(controller, state):
    with pytest.raises(NotFoundError):
        run_hypothesis_test(controller, state, "nope", "x", passed=True)


def test_compare_segments_records_observation(controller, state, sales_df):
    result = compare_segments(controller, state, sales_df, "product", "revenue", "B", "C")
    assert result["diff"] == 230 - 20
    assert len(state.observations) == 1
    assert "compare_segments" in state.observations[0].description


def test_drill_down_with_filter_and_top_n(controller, state, sales_df):
    rows = drill_down(
        controller, state, sales_df,
        group_cols="product", metric_col="revenue",
        filter_col="region", filter_op="==", filter_value="east",
        top_n=1,
    )
    assert len(rows) == 1
    assert rows[0]["product"] == "B"
    assert len(state.observations) == 1


def test_evaluate_evidence_links_to_test(controller, state):
    hyp = create_hypothesis(controller, state, "H1")
    test = run_hypothesis_test(controller, state, hyp.id, "t", passed=True)
    ev = evaluate_evidence(controller, state, "confirmed via inventory data", test_id=test.id, contribution_pct=60.0)
    assert ev.test_id == test.id
    assert len(state.evidence) == 1


def test_evaluate_evidence_unknown_test_raises(controller, state):
    with pytest.raises(NotFoundError):
        evaluate_evidence(controller, state, "x", test_id="nope")


def test_evaluate_evidence_triggers_enough_evidence_status(controller, state):
    from investigation_engine.state import InvestigationStatus
    evaluate_evidence(controller, state, "single sufficient piece of evidence")
    assert state.status == InvestigationStatus.ENOUGH_EVIDENCE


def test_verify_finding_requires_existing_evidence(controller, state):
    with pytest.raises(NotFoundError):
        verify_finding(controller, state, "conclusion", evidence_ids=["nope"])


def test_verify_finding_success(controller, state):
    ev = evaluate_evidence(controller, state, "evidence text")
    finding = verify_finding(
        controller, state, "Revenue drop driven by product B stockout in west",
        evidence_ids=[ev.id], limitations=["only 2 weeks of data"],
    )
    assert finding in state.findings
    assert finding.limitations == ["only 2 weeks of data"]
