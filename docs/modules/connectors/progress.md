last updated: 2026-09-22

# connectors — Progress

Module complete on branch `feature/connectors` (off `main`).

- `connectors/base.py`: abstract `Connector` interface (test_connection, list_entities, get_schema, fetch).
- `connectors/csv_connector.py`: directory-of-CSVs connector, whole-file reads.
- `connectors/postgres_connector.py`: SQLAlchemy-based, bound params, quoted identifiers. Live-tested against a throwaway `postgres:16-alpine` Docker container (removed after testing) — same convention causly-server's data-catalog phase used.
- `connectors/registry.py`: `DatasetRegistry` — holds registered connectors + in-memory materialized datasets (`DatasetHandle`). Backs the 4 data-access tools; enforces "LLM never sees raw datasets directly" by having quality tools operate on `dataset_id`, not raw rows.
- `connectors/quality.py`: 8 data-quality check functions (report-only, never mutate).
- `connectors/contracts.py` + `connectors/gateway_adapter.py`: pydantic I/O schemas + `make_connector_contracts(registry)` wiring all 12 tools into `tool_gateway.ToolContract` (READ_DATA, except `materialize_dataset` which needs ARTIFACT_WRITE).
- Tests: `test_connectors_csv.py`, `test_connectors_registry.py`, `test_connectors_quality.py`, `test_connectors_gateway_adapter.py` (39/39, no external deps), `test_connectors_postgres.py` (8/8, skips automatically if no live Postgres reachable at `localhost:55432/testdb`).
- Added `psycopg2-binary` and `pyarrow` to requirements.txt.
- Remaining for later modules: `fetch_dataset`/`query_data` filters are V1 equality-only per spec; CSV connector reads whole files (no streaming) — both are known, deliberate V1 scope limits, not bugs.
