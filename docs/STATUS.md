last updated: 2026-09-23

Current active module: none (artifacts-visualization just finished — pick next from Module Status below)

# Module Status

- agent-core — ✅ done (branch feature/agent-core, off feature/tool-gateway; all tasks complete, 134/134 total tests passing)
- tool-gateway — ✅ done (branch feature/tool-gateway; all tasks complete, 44/44 tests passing)
- execution-backend — 🔧 in-progress (branch feature/execution-backend, not yet merged to main; LocalExecutor + AST validator + subprocess timeout/memory limits built, 160/160 tests passing on that branch; remaining: register execute_code contract with ToolGateway in server.py)
- data-catalog — ✅ done (branch feature/data-catalog, off main; SQLite storage, all 4 tools + authority resolution built, 15 new tests, 149/149 passing on main baseline)
- connectors — ✅ done (branch feature/connectors, off main; base Connector interface + DatasetRegistry + 8 data-quality checks + 12 tools registered with tool-gateway, plus 17 connectors — CSV, Excel, MySQL, Postgres, Notion, Slack, Google Drive, Stripe, BigQuery, GA4, Mixpanel, WooCommerce, Salesforce, HubSpot, QuickBooks, Teams, Shopify, Snowflake — 164/164 tests passing, 16 skip without live DB containers up)
- investigation-engine — ✅ done (branch feature/investigation-engine, off main; State schema, persistence, full analytical engine, bounded loop controller, 6 tools + tool-gateway registration all built; 72/72 module tests passing, 247/247 full-repo suite passing)
- artifacts-visualization — ✅ done, pending PR (branch feature/artifacts-visualization; all 5 tasks complete: chart_generators moved to artifacts_visualization/, generate_chart/export_dataset/generate_report/finalize_artifact/list_artifacts/regenerate_artifact wired into tool-gateway with SQLite-backed persistence; 15/15 module tests, 426/426 full-repo suite)
- desktop-app — ⬜ pending
- landing-page — ⬜ pending (static site, detail TBD when started)

Legend: pending / in-progress / done
