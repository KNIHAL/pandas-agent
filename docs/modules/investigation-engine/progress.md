last updated: 2026-09-23

# investigation-engine — Progress

- Investigation State schema built (investigation_engine/state.py):
  question/intent/sources/queries/observations/hypotheses/tests/evidence/findings/conclusion/artifacts chain, Bounds, dup-query-hash tracking, to_dict/from_dict roundtrip.
- Persistence built (investigation_engine/persistence.py): InvestigationStore interface, InMemoryInvestigationStore (default/test fallback), RedisInvestigationStore (JSON blob, TTL), get_default_store() auto-picks Redis if reachable else in-memory.
- 10/10 tests passing (tests/test_investigation_engine_state.py, tests/test_investigation_engine_persistence.py).
- redis not yet added to requirements.txt (optional import, guarded) -- add it when RedisInvestigationStore is actually wired into a live path.
- Analytical engine core ops built (investigation_engine/analytics/core.py): filter_rows, sort_rows, aggregate, group_by, calc_metric_change, segment (with pct_of_total for driver ranking, per spec step 4).
- 23/23 tests passing total for the module so far.
- 3 enterprise-hardening gaps (large-data safeguards, access control, concurrency) logged in DECISIONS.md, deferred to live E2E testing phase alongside DuckDB/Qdrant -- not in current scope.
- Next up: analytical engine statistical ops (distribution/correlation/percentile/variance).
