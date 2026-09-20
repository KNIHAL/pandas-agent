last updated: 2026-09-20

# investigation-engine — Spec

## What
- Panda's core differentiator: adaptive bounded investigation loop (not rigid waterfall).
- Flow: Question → Understand → Find Source → Query → Validate → Analyze → Find Driver → Investigate → Hypothesis → Test → Verify → Enough Evidence? (No → fetch more / Yes → Finding → Artifact)
- Bounded by: stopping criteria, iteration limits, query limits, timeout, duplicate-query protection, evidence requirements.

## Tools
- create_hypothesis, test_hypothesis, compare_segments, drill_down, evaluate_evidence, verify_finding

## Investigation State (persisted, likely Redis)
- Question → Intent → Sources → Queries → Observations → Hypotheses → Tests → Evidence → Findings → Conclusion → Artifacts
- Purpose: follow-up questions don't redo full analysis.

## Analytical engine (used by this module)
- Core: aggregation, grouping, filtering, sorting, metric calc, segmentation
- Statistical: distribution, correlation, percentile, variance analysis
- Time-series: period comparison, % change, trend detection, anomaly detection
- Business: contribution analysis, driver analysis, segment analysis

## Behavior bar (how a good investigation should look — reference example)
- Reference case: "Why did my sales drop in August?"
  1. Understand question → metric=revenue, period=August, comparison=prev period, type=root-cause.
  2. Pick authoritative source from data-catalog (not all sources) → query only that.
  3. Compute the top-level number itself (e.g. change = -27.8%) and pass agent a small structured result, never raw rows.
  4. Break metric into candidate drivers (orders, AOV, products, customers, geography, discounts) and measure which one explains most of the change.
  5. Drill into the biggest driver (e.g. one product's unit sales), cross-check against another signal (e.g. inventory/stockout data).
  6. Form an explicit hypothesis, then test it: timing fits? magnitude fits? % contribution to total decline? any alternative explanation ruled out? supporting data actually available?
  7. Quantify contribution (e.g. "~68% of the decline") before stating it as the answer.
  8. Final answer = the metric change + the strongest supported driver + the quantified evidence + an explicit limitation if some data source wasn't available. Never a vague guess like "customers probably lost interest."
- Rule of thumb: no claim in the final answer without a number or a checked fact behind it. If evidence is weak, say so — don't round up to confidence.
