last updated: 2026-09-23

# artifacts-visualization — Progress

- Moved/adapted `core/chart_generators/*` -> `artifacts_visualization/` (bar/line/pie generators + templates + base).
- Fixed `_save_chart` path logic in base.py for new location (charts/ output dir, templates/ dir).
- Added `contracts.py` (ChartColumn, GenerateChartInput/Output) and `gateway_adapter.py`
  (`make_artifacts_visualization_contracts`) registering one tool: `generate_chart`
  (chart_type: bar/line/pie, permission: ARTIFACT_WRITE) — same pattern as
  investigation-engine's adapter.
- Added tests/test_artifacts_visualization_gateway_adapter.py — 5/5 passing.
  Full repo suite: 416 passed, 16 skipped (pre-existing, DB-dependent).
- Old `core/chart_generators/*` and `core/visualization.py` left untouched — not deleted yet,
  server.py's legacy `generate_chartjs_tool` still points at them directly (not through gateway).
- Next: CSV/Excel/PDF/report export tools.
