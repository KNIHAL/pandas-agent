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
- Added `exporters.py` (export_csv/export_excel/export_pdf_table/export_report, reportlab-based
  for PDF, output to <repo_root>/exports/) + 2 more gateway tools: `export_dataset`
  (csv/excel/pdf, permission ARTIFACT_WRITE) and `generate_report` (PDF from title +
  heading/body sections, permission ARTIFACT_WRITE). Added reportlab>=5.0.0 to requirements.txt.
- 11/11 module tests passing (5 chart + 6 new export/report).
- Next: artifact persistence (finalized dataset/report storage).
