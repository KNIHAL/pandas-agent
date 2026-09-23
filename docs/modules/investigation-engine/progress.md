last updated: 2026-09-23

# investigation-engine — Progress

- Investigation State schema built (investigation_engine/state.py):
  question/intent/sources/queries/observations/hypotheses/tests/evidence/findings/conclusion/artifacts chain, Bounds, dup-query-hash tracking, to_dict/from_dict roundtrip.
- Persistence built (investigation_engine/persistence.py): InvestigationStore interface, InMemoryInvestigationStore (default/test fallback), RedisInvestigationStore (JSON blob, TTL), get_default_store() auto-picks Redis if reachable else in-memory.
- 10/10 tests passing (tests/test_investigation_engine_state.py, tests/test_investigation_engine_persistence.py).
- redis not yet added to requirements.txt (optional import, guarded) -- add it when RedisInvestigationStore is actually wired into a live path.
- Next up: analytical engine core ops (aggregation/grouping/filtering/sorting/metric calc/segmentation).
