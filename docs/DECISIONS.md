last updated: 2026-09-21

# Decisions Log (append-only, dated, short)

- 2026-09-20 — Dropping CrewAI, building agent loop from scratch in Python. Why: no dependency on any agentic framework, full control over reasoning/tool-selection loop.
- 2026-09-20 — Adopted docs/ structure (OVERVIEW, HOW_TO_WORK, STATUS, DECISIONS, modules/*) for per-module dedicated chats. Why: avoid re-feeding full spec every chat, save tokens, keep each module self-contained.
- 2026-09-20 — Reuse `core/chart_generators/*` as-is (no CrewAI/MCP coupling in that code). Why: clean OOP, framework-independent already.
- 2026-09-20 — Module code directories use snake_case (e.g. `tool_gateway/`), not the kebab-case used by `docs/modules/<name>/`. Why: Python can't import a hyphenated package name; snake_case is the only workable choice for every future module's code dir.
- 2026-09-20 — `ToolGateway.get_contract(name)` added after tool-gateway was marked done, while building agent-core's Tool Gateway hook-up. Why: agent-core needs the full `ToolContract` (not just names from `list_tools()`) to build LLM-facing `ToolSpec`s.
- 2026-09-21 — data-catalog storage: SQLite via SQLAlchemy, not Postgres (tasks.md's original guess). Why: catalog entries are metadata about data sources, not the data itself; app is a bundled desktop app with no external services and won't be touched after initial build — zero-ops storage fits, enterprise adoption shouldn't require standing up a DB just for catalog metadata.
- 2026-09-21 — data-catalog authority resolution uses a normalized `metric_authority` table (unique on metric_name) instead of a boolean flag scanned across JSON blobs. Why: DB-level guarantee of exactly one authoritative entry per metric, not just convention; conflicting claims raise `AuthorityConflictError` unless explicitly forced.
- 2026-09-22 — connectors: `fetch_dataset`/`materialize_dataset`/`release_dataset` operate on an in-memory `DatasetRegistry` handle (`dataset_id`), not raw rows. Why: enforces agent-core's "LLM never sees raw datasets directly" rule at the connectors layer so every future tool built on a materialized dataset inherits it for free, instead of each tool re-implementing the boundary.
- 2026-09-22 — connectors Postgres support uses SQLAlchemy + psycopg2-binary (bound params, quoted identifiers), consistent with data_catalog/db.py's engine pattern, rather than a separate driver/ORM. Why: one DB access pattern across the codebase; live-tested against a throwaway Docker container per the causly-server testing convention.
