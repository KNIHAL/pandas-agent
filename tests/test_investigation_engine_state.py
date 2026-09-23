from investigation_engine.state import (
    Bounds,
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    InvestigationStatus,
)


def test_new_creates_active_state_with_defaults():
    s = InvestigationState.new("Why did sales drop in August?")
    assert s.status == InvestigationStatus.ACTIVE
    assert s.question == "Why did sales drop in August?"
    assert s.iteration_count == 0
    assert s.bounds.max_iterations == 8


def test_duplicate_query_protection():
    s = InvestigationState.new("q")
    assert s.is_duplicate_query("h1") is False
    s.register_query_hash("h1")
    assert s.is_duplicate_query("h1") is True


def test_has_enough_evidence_respects_bounds():
    s = InvestigationState.new("q", bounds=Bounds(min_evidence_items=2))
    assert s.has_enough_evidence() is False
    s.evidence.append(__import__("investigation_engine.state", fromlist=["Evidence"]).Evidence(id="e1", test_id=None, description="x"))
    assert s.has_enough_evidence() is False
    s.evidence.append(__import__("investigation_engine.state", fromlist=["Evidence"]).Evidence(id="e2", test_id=None, description="y"))
    assert s.has_enough_evidence() is True


def test_is_over_bounds_on_iteration_limit():
    s = InvestigationState.new("q", bounds=Bounds(max_iterations=2))
    s.iteration_count = 2
    assert s.is_over_bounds() is True


def test_is_over_bounds_on_query_limit():
    s = InvestigationState.new("q", bounds=Bounds(max_queries=1))
    from investigation_engine.state import Query
    s.queries.append(Query(id="q1", source_id="src1", query="select 1"))
    assert s.is_over_bounds() is True


def test_roundtrip_to_dict_from_dict_preserves_data():
    s = InvestigationState.new("Why did sales drop?")
    s.hypotheses.append(Hypothesis(id="h1", statement="Product X stockout", status=HypothesisStatus.TESTING))
    s.register_query_hash("abc123")

    d = s.to_dict()
    restored = InvestigationState.from_dict(d)

    assert restored.id == s.id
    assert restored.question == s.question
    assert restored.hypotheses[0].statement == "Product X stockout"
    assert restored.hypotheses[0].status == HypothesisStatus.TESTING
    assert restored.seen_query_hashes == {"abc123"}
    assert restored.status == InvestigationStatus.ACTIVE
