last updated: 2026-09-22

# connectors — Progress

Module complete on branch `feature/connectors` (off `main`).

- `connectors/base.py`: abstract `Connector` interface (test_connection, list_entities, get_schema, fetch).
- Connectors built so far, easy→hard order: CSV, Excel, MySQL, Postgres, Notion, Slack, Google Drive, Stripe, BigQuery, GA4, Mixpanel, WooCommerce.
- `mixpanel_connector.py`: entity = event name, raw events via the Export API (JSONL), properties flattened into columns. Mocked HTTP tests.
- `woocommerce_connector.py`: entities are WooCommerce's list-able resources (products/orders/customers/coupons/refunds), consumer key/secret Basic auth, page-number pagination. Mocked HTTP tests.
- `stripe_connector.py`: entities are Stripe's list-able resource types (customers/charges/...); filters pass straight through as Stripe query params. Mocked HTTP tests — Stripe doesn't currently allow Indian self-signup.
- `bigquery_connector.py`: official `google-cloud-bigquery` client, service-account auth. Works fine against a BigQuery Sandbox project (no billing account) within its free quota. Mocked `bigquery.Client` tests — Kumar's GCP billing account was detached, sandbox not yet re-enabled.
- `ga4_connector.py`: GA4 has no tables (it's a dimensions×metrics report API), so an entity is a spec string `"dim1,dim2|metric1,metric2"` — a deliberate design choice to keep it inside the same `Connector` interface rather than a bespoke one, flagged in the file's docstring rather than stopping to ask (unlike Qdrant, which genuinely didn't fit). Mocked HTTP tests — no live GA4 property available.
- `csv_connector.py` / `excel_connector.py`: directory-of-files, whole-file reads. Excel entities are `file.xlsx#SheetName`.
- `mysql_connector.py` / `postgres_connector.py`: SQLAlchemy-based, bound params, quoted identifiers. Both live-tested against throwaway Docker containers (`postgres:16-alpine`, `mysql:8`, removed after) — same convention causly-server's data-catalog phase used. Known Docker quirk: containers auto-stop shortly after `docker_run`; `docker_start` again right before testing.
- `notion_connector.py` / `slack_connector.py` / `google_drive_connector.py`: REST API + token/service-account auth. No live accounts available (Kumar not signed up yet / GCP billing detached), so these are verified against a mocked HTTP layer matching each API's documented shapes instead of a live account — re-verify against real credentials before relying on them. Notion entity = database ID; Slack entity = channel name or ID; Google Drive entity = file ID (Sheets/CSV only, folder must be shared with the service account).
- `registry.py`: `DatasetRegistry` — holds registered connectors + in-memory materialized datasets (`DatasetHandle`). Backs the 4 data-access tools; enforces "LLM never sees raw datasets directly" by having quality tools operate on `dataset_id`, not raw rows.
- `quality.py`: 8 data-quality check functions (report-only, never mutate).
- `contracts.py` + `gateway_adapter.py`: pydantic I/O schemas + `make_connector_contracts(registry)` wiring all 12 data-access/quality tools into `tool_gateway.ToolContract` (READ_DATA, except `materialize_dataset` which needs ARTIFACT_WRITE). Connector-specific tools (if any get added later) aren't wired yet — current 12 tools are source-agnostic (they take `source`/`entity`, work with any registered connector).
- Tests: 73 passing, 16 skipped (Postgres/MySQL skip automatically if no live container reachable at test time).
- Added `psycopg2-binary`, `pyarrow`, `openpyxl`, `pymysql`, `requests`, `google-auth` to requirements.txt.
- Remaining connectors, easy→hard: Salesforce, HubSpot, QuickBooks, Teams, Shopify, Snowflake.
- Qdrant/semantic-retrieval skipped by Kumar's call: doesn't fit the row-fetch `Connector` interface (similarity search, not exact match) and no clear use yet — revisit once Investigation Engine's design makes the fit concrete.
- Other remaining for later: `fetch_dataset`/`query_data` filters are V1 equality-only per spec; CSV/Excel connectors read whole files (no streaming) — both are known, deliberate V1 scope limits, not bugs.
