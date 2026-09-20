last updated: 2026-09-20

# artifacts-visualization — Spec

## What
- Analysis doesn't stay chat-only — gets saved as artifacts: charts, CSV, Excel, PDF, analysis reports, finalized datasets, investigation records.
- Flow: Source → Working Dataset → Analysis → Finalized Dataset/Artifact. Working data is temporary; finalized output persists.

## Visualization
- Types: line, bar, distributions, comparisons, contribution charts, anomaly/trend charts.
- Generated FROM analysis state, not re-derived. If user says "graph bana do" later, reuse existing result — don't redo analysis.

## Legacy — reusable
- `core/chart_generators/*` (base/bar/line/pie + HTML templates) already framework-independent, no CrewAI/MCP coupling.
- Plan: keep this code, just re-wire it to be called via tool-gateway instead of directly.
