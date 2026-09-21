last updated: 2026-09-21

# data-catalog — Progress

- Core module built: `data_catalog/` — models.py (CatalogEntry + MetricAuthority ORM), db.py (SQLite engine/session, `:memory:` supported for tests), errors.py, repository.py (CatalogRepository: upsert_entry, list_sources, inspect_source, inspect_schema, find_data, resolve_authority), contracts.py (pydantic I/O), gateway_adapter.py (4 ToolContracts).
- Storage decision: SQLite over Postgres — this is metadata about data sources, not the data itself; app ships as a bundled desktop app with no external services (per OVERVIEW.md) and won't be touched after initial build, so zero-ops storage was the right call. Logged in DECISIONS.md.
- Authority resolution uses a normalized `metric_authority` table (metric_name unique) rather than scanning JSON blobs — DB-level guarantee of exactly one authoritative entry per metric. `upsert_entry(..., authority=True)` raises `AuthorityConflictError` on a conflicting claim unless `force_authority=True`.
- `find_data` does an in-Python substring scan across all entries rather than SQL/FTS — catalog entries are metadata (low thousands of rows expected even at enterprise scale), simplicity favored over premature optimization. Revisit with SQLite FTS5 if that assumption breaks.
- Only the 4 spec'd tools are gateway-exposed; `upsert_entry`/`resolve_authority` are plain repository methods for connectors/investigation-engine to call directly, not agent-facing tools.
- Tests: `tests/test_data_catalog_repository.py`, `tests/test_data_catalog_gateway_adapter.py` — 15 new tests, 149/149 passing on `main` baseline (execution-backend's 20 tests are on its own unmerged branch, not counted here).
- Branched off `main` as `feature/data-catalog` (independent of execution-backend, no shared dependency).
