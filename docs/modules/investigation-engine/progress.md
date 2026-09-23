last updated: 2026-09-23

# investigation-engine — Progress

Module complete. Branch `feature/investigation-engine` off `main`.

Files (all under `investigation_engine/`):
- `state.py` — InvestigationState: question/intent/sources/queries/observations/hypotheses/tests/evidence/findings/conclusion/artifacts chain, Bounds, dup-query-hash tracking, to_dict/from_dict roundtrip.
- `persistence.py` — InvestigationStore interface, InMemoryInvestigationStore (default/test fallback), RedisInvestigationStore (JSON blob, TTL), get_default_store() auto-picks Redis if reachable else in-memory. `redis` not yet added to requirements.txt (optional import, guarded) — add when actually wired to a live path.
- `analytics/core.py` — filter_rows, sort_rows, aggregate, group_by, calc_metric_change, segment.
- `analytics/statistical.py` — distribution, percentile, correlation, variance_analysis.
- `analytics/time_series.py` — period_comparison, trend, detect_anomalies (z-score based).
- `analytics/business.py` — contribution_analysis, driver_analysis (period-over-period, ranked by contribution to change), compare_segments, rank_volatile_segments. The analytical engine is internal — not agent-facing, only the 6 tools below are gateway-exposed.
- `loop_controller.py` — InvestigationLoopController: begin_iteration (iteration/timeout bounds), record_query (dup protection via query hash + max_queries bound), check_evidence_sufficiency, complete.
- `tools.py` — the 6 agent-facing tools: create_hypothesis, test_hypothesis, compare_segments, drill_down, evaluate_evidence, verify_finding. Each mutates + persists InvestigationState and returns small structured results (never raw rows). verify_finding validates cited evidence_ids exist; test_hypothesis validates hypothesis_id; evaluate_evidence validates test_id and triggers the loop controller's enough-evidence check.
- `contracts.py` — pydantic input/output schemas for the 6 tools.
- `gateway_adapter.py` — make_investigation_engine_contracts(store) wires the 6 tools into tool_gateway.ToolContract, following data_catalog's adapter pattern (factory returns list[ToolContract], handlers take one input model, return one output model).

Design note: compare_segments/drill_down take `data: list[dict]` (records the caller already fetched) rather than a dataset_id + live source fetch — that fetch is a connectors/execution-backend integration this module doesn't own. Logged in DECISIONS.md, revisit at E2E phase.

Tests: 72/72 passing for this module (state, persistence, analytics x4, loop_controller, tools, gateway_adapter). Full repo suite: 247/247 passing, no regressions.

3 enterprise-hardening gaps (large-data safeguards, access control, concurrent investigations) logged in DECISIONS.md, deferred to live E2E testing phase alongside DuckDB/Qdrant — not in current scope.

Next module per STATUS.md: artifacts-visualization or whichever is picked up next.
