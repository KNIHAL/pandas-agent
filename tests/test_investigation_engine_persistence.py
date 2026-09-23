from investigation_engine.persistence import InMemoryInvestigationStore
from investigation_engine.state import InvestigationState


def test_in_memory_store_save_and_load_roundtrip():
    store = InMemoryInvestigationStore()
    s = InvestigationState.new("Why did sales drop in August?")
    s.register_query_hash("q1")
    store.save(s)

    loaded = store.load(s.id)
    assert loaded is not None
    assert loaded.id == s.id
    assert loaded.question == s.question
    assert loaded.seen_query_hashes == {"q1"}


def test_in_memory_store_load_missing_returns_none():
    store = InMemoryInvestigationStore()
    assert store.load("does-not-exist") is None


def test_in_memory_store_delete():
    store = InMemoryInvestigationStore()
    s = InvestigationState.new("q")
    store.save(s)
    store.delete(s.id)
    assert store.load(s.id) is None


def test_save_updates_updated_at():
    store = InMemoryInvestigationStore()
    s = InvestigationState.new("q")
    before = s.updated_at
    store.save(s)
    assert s.updated_at >= before
