last updated: 2026-09-22



# Module Status

- agent-core — ✅ done (branch feature/agent-core, off feature/tool-gateway; all tasks complete, 134/134 total tests passing)
- tool-gateway — ✅ done (branch feature/tool-gateway; all tasks complete, 44/44 tests passing)
- execution-backend — 🔧 in-progress (branch feature/execution-backend, not yet merged to main; LocalExecutor + AST validator + subprocess timeout/memory limits built, 160/160 tests passing on that branch; remaining: register execute_code contract with ToolGateway in server.py)
- data-catalog — ✅ done (branch feature/data-catalog, off main; SQLite storage, all 4 tools + authority resolution built, 15 new tests, 149/149 passing on main baseline)
- connectors — ✅ done (branch feature/connectors, off main; base Connector interface + DatasetRegistry + 8 data-quality checks + 12 tools registered with tool-gateway, plus 17 connectors — CSV, Excel, MySQL, Postgres, Notion, Slack, Google Drive, Stripe, BigQuery, GA4, Mixpanel, WooCommerce, Salesforce, HubSpot, QuickBooks, Teams, Shopify, Snowflake — 164/164 tests passing, 16 skip without live DB containers up)
- investigation-engine — ⬜ pending
- artifacts-visualization — ⬜ pending (legacy `core/chart_generators/*` exists, reusable as-is)
- desktop-app — ⬜ pending


Legend: pending / in-progress / done
