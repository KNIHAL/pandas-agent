import time

import pytest

from investigation_engine.loop_controller import (
    BoundsExceededError,
    DuplicateQueryError,
    InvestigationLoopController,
    hash_query,
)
from investigation_engine.persistence import InMemoryInvestigationStore
from investigation_engine.state import Bounds, Evidence, InvestigationStatus


@pytest.fixture
def controller():
    return InvestigationLoopController(store=InMemoryInvestigationStore())


def test_start_persists_state(controller):
    state = controller.start("Why did sales drop?")
    loaded = controller.load(state.id)
    assert loaded is not None
    assert loaded.question == "Why did sales drop?"


def test_begin_iteration_increments_count(controller):
    state = controller.start("q")
    controller.begin_iteration(state)
    assert state.iteration_count == 1
    controller.begin_iteration(state)
    assert state.iteration_count == 2


def test_begin_iteration_raises_when_over_bounds(controller):
    state = controller.start("q", bounds=Bounds(max_iterations=1))
    controller.begin_iteration(state)
    with pytest.raises(BoundsExceededError):
        controller.begin_iteration(state)
    assert state.status == InvestigationStatus.STOPPED_LIMIT


def test_begin_iteration_raises_on_timeout(controller):
    state = controller.start("q", bounds=Bounds(timeout_seconds=0))
    time.sleep(0.01)
    with pytest.raises(BoundsExceededError):
        controller.begin_iteration(state)
    assert state.status == InvestigationStatus.STOPPED_LIMIT


def test_record_query_registers_and_dedupes(controller):
    state = controller.start("q")
    controller.record_query(state, "src1", "SELECT * FROM sales")
    assert len(state.queries) == 1
    with pytest.raises(DuplicateQueryError):
        controller.record_query(state, "src1", "SELECT * FROM sales")
    # case/whitespace-insensitive dedup
    with pytest.raises(DuplicateQueryError):
        controller.record_query(state, "src1", "  select * from sales  ")


def test_record_query_different_source_not_duplicate(controller):
    state = controller.start("q")
    controller.record_query(state, "src1", "SELECT * FROM sales")
    q2 = controller.record_query(state, "src2", "SELECT * FROM sales")
    assert q2.source_id == "src2"
    assert len(state.queries) == 2


def test_record_query_raises_when_max_queries_hit(controller):
    state = controller.start("q", bounds=Bounds(max_queries=1))
    controller.record_query(state, "src1", "q1")
    with pytest.raises(BoundsExceededError):
        controller.record_query(state, "src1", "q2")
    assert state.status == InvestigationStatus.STOPPED_LIMIT


def test_check_evidence_sufficiency_transitions_status(controller):
    state = controller.start("q", bounds=Bounds(min_evidence_items=1))
    assert state.status == InvestigationStatus.ACTIVE
    state.evidence.append(Evidence(id="e1", test_id=None, description="x"))
    controller.check_evidence_sufficiency(state)
    assert state.status == InvestigationStatus.ENOUGH_EVIDENCE


def test_should_stop_true_when_enough_evidence(controller):
    state = controller.start("q", bounds=Bounds(min_evidence_items=1))
    state.evidence.append(Evidence(id="e1", test_id=None, description="x"))
    controller.check_evidence_sufficiency(state)
    assert controller.should_stop(state) is True


def test_complete_sets_status(controller):
    state = controller.start("q")
    controller.complete(state)
    assert state.status == InvestigationStatus.COMPLETE
    assert controller.should_stop(state) is True


def test_hash_query_is_deterministic_and_normalizes():
    h1 = hash_query("src1", "SELECT * FROM sales")
    h2 = hash_query("src1", "  select * from sales  ")
    h3 = hash_query("src2", "SELECT * FROM sales")
    assert h1 == h2
    assert h1 != h3
