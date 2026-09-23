last updated: 2026-09-22

# Decisions Log (append-only, dated, short)

- 2026-09-20 -- Dropping CrewAI, building agent loop from scratch in Python. Why: no dependency on any agentic framework, full control over reasoning/tool-selection loop.
- 2026-09-20 -- Adopted docs/ structure (OVERVIEW, HOW_TO_WORK, STATUS, DECISIONS, modules/*) for per-module dedicated chats. Why: avoid re-feeding full spec every chat, save tokens, keep each module self-contained.
- 2026-09-20 -- Reuse `core/chart_generators/*` as-is (no CrewAI/MCP coupling in that code). Why: clean OOP, framework-independent already.
- 2026-09-20 -- Module code directories use snake_case (e.g. `tool_gateway/`), not the kebab-case used by `docs/modules/<name>/`. Why: Python can't import a hyphenated package name; snake_case is the only workable choice for every future module's code dir.
- 2026-09-20 -- `ToolGateway.get_contract(name)` added after tool-gateway was marked done, while building agent-core's Tool Gateway hook-up. Why: agent-core needs the full `ToolContract` (not just names from `list_tools()`) to build LLM-facing `ToolSpec`s.
- 2026-09-21 -- data-catalog storage: SQLite via SQLAlchemy, not Postgres (tasks.md's original guess). Why: catalog entries are metadata about data sources, not the data itself; app is a bundled desktop app with no external services and won't be touched after initial build -- zero-ops storage fits, enterprise adoption shouldn't require standing up a DB just for catalog metadata.
- 2026-09-21 -- data-catalog authority resolution uses a normalized `metric_authority` table (unique on metric_name) instead of a boolean flag scanned across JSON blobs. Why: DB-level guarantee of exactly one authoritative entry per metric, not just convention; conflicting claims raise `AuthorityConflictError` unless explicitly forced.
- 2026-09-22 -- Deferred Qdrant (semantic retrieval connector) and DuckDB (execution-backend allowed lib) out of V1 builds entirely. Why: both need real data + real end-to-end flow to build/test meaningfully; building them isolated now risks guesswork and rework. Will implement during live end-to-end testing phase, not as part of any single module's build.
- 2026-09-23 -- Deferred 3 enterprise-hardening gaps found during investigation-engine build, to be implemented together at live E2E testing phase (alongside Qdrant/DuckDB above). Why: each needs a real cross-module contract, not a guess made in isolation.
  - Large-data safeguards (sampling/row-limits for big tables): touches investigation-engine's analytical engine + execution-backend (query execution) + connectors (source-level limits).
  - Access control (row/column-level permission checks): touches data-catalog + connectors, not just investigation-engine.
  - Concurrent investigations (resource contention when multiple users/questions run at once): investigation-engine loop controller, needs real concurrency load to size correctly.
