last updated: 2026-09-21

# data-catalog — Tasks

- [x] Define catalog entry schema (source/entity/table/fields/metrics/dimensions/date fields/authority/freshness/relationships/permissions/lineage)
- [x] Storage for catalog (SQLite via SQLAlchemy — no external DB service, fits bundled desktop app; see DECISIONS.md)
- [x] `list_sources` / `inspect_source` / `inspect_schema` / `find_data` tools
- [x] Authority resolution logic (which source wins per metric) — separate `metric_authority` table, DB-enforced one-authority-per-metric, `force=True` to reassign
