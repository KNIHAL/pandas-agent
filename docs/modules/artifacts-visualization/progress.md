last updated: 2026-09-24

# artifacts-visualization — Progress

- Moved/adapted `core/chart_generators/*` -> `artifacts_visualization/` (bar/line/pie generators + templates + base).
- Fixed `_save_chart` path logic in base.py for new location (charts/ output dir, templates/ dir).
- Added `contracts.py` (ChartColumn, GenerateChartInput/Output, ExportDatasetInput/Output,
  ReportSection, GenerateReportInput/Output, FinalizeArtifactInput/Output, ListArtifactsInput/Output,
  RegenerateArtifactInput/Output).
- Added `exporters.py` (export_csv/export_excel/export_pdf_table via pandas, export_report via
  reportlab), output to <repo_root>/exports/. Added reportlab>=5.0.0 to requirements.txt.
- Added persistence layer: `models.py` (ArtifactRecord: type/title/file_path/generator_config),
  `db.py` (SQLite, default artifacts_visualization/artifacts.db, same pattern as data_catalog),
  `repository.py` (ArtifactRepository: finalize/get/list), `errors.py` (ArtifactNotFoundError).
- `gateway_adapter.py` (`make_artifacts_visualization_contracts(repo, ...)`, repo now a required
  param) registers 6 tools: generate_chart, export_dataset, generate_report, finalize_artifact,
  list_artifacts, regenerate_artifact. regenerate_artifact rebuilds a finalized artifact's file
  from its stored generator_config -- no re-analysis needed.
- Fixed a filename-collision bug surfaced by regenerate testing: base.py/exporters.py filenames
  used `int(time.time())` only, so a chart generated then immediately regenerated in the same
  second collided. Both now add a short uuid suffix.
- 15/15 module tests passing. Full repo suite: 426 passed, 16 skipped (pre-existing, DB-dependent).
- Old `core/chart_generators/*` and `core/visualization.py` left untouched — server.py's legacy
  `generate_chartjs_tool` still points at them directly (not through gateway) — out of scope for
  this module.
- All planned tasks complete. Not yet opened as a PR.
