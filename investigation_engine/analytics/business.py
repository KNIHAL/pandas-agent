"""Business analytical ops: contribution analysis, driver analysis,
segment comparison. These sit on top of core/statistical/time_series
and produce the "candidate driver" and "ranked contribution" shapes
the investigation loop's tools consume directly (spec: hypothesis
generation from decomposition, ranking evidence by contribution).
"""
from __future__ import annotations

import pandas as pd

from investigation_engine.analytics.core import calc_metric_change, group_by, segment
from investigation_engine.analytics.statistical import variance_analysis


def contribution_analysis(
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    agg: str = "sum",
    top_n: int | None = None,
) -> pd.DataFrame:
    """Rank segments by their contribution to the total metric.
    Thin, semantically-named wrapper over segment() for the business
    layer's vocabulary (used directly by tools like compare_segments)."""
    return segment(df, segment_col, metric_col, func=agg, top_n=top_n)


def driver_analysis(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    agg: str = "sum",
) -> pd.DataFrame:
    """Compare a metric across two periods, broken down by segment, and
    rank segments by their contribution to the overall change. This is
    the core "why did the metric move" decomposition (spec step 4/5:
    break the metric into candidate drivers, then rank by contribution)."""
    current_grouped = group_by(current_df, segment_col, metric_col, agg).set_index(segment_col)
    previous_grouped = group_by(previous_df, segment_col, metric_col, agg).set_index(segment_col)

    all_segments = sorted(set(current_grouped.index) | set(previous_grouped.index))
    rows = []
    total_change = 0.0
    changes = []
    for seg_value in all_segments:
        cur = float(current_grouped[metric_col].get(seg_value, 0.0))
        prev = float(previous_grouped[metric_col].get(seg_value, 0.0))
        change = calc_metric_change(cur, prev)
        changes.append((seg_value, change))
        total_change += change["abs_change"]

    for seg_value, change in changes:
        contribution_pct = (
            (change["abs_change"] / total_change * 100.0) if total_change else 0.0
        )
        rows.append(
            {
                segment_col: seg_value,
                "current": change["current"],
                "previous": change["previous"],
                "abs_change": change["abs_change"],
                "pct_change": change["pct_change"],
                "contribution_to_total_change_pct": contribution_pct,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.reindex(
        out["abs_change"].abs().sort_values(ascending=False).index
    ).reset_index(drop=True)


def compare_segments(
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    segment_a,
    segment_b,
    agg: str = "sum",
) -> dict:
    """Head-to-head comparison of two specific segment values on one
    metric -- used to test a hypothesis like "is region east
    underperforming region west"."""
    grouped = group_by(df, segment_col, metric_col, agg).set_index(segment_col)
    val_a = float(grouped[metric_col].get(segment_a, 0.0))
    val_b = float(grouped[metric_col].get(segment_b, 0.0))
    return {
        segment_col: {segment_a: val_a, segment_b: val_b},
        "diff": val_a - val_b,
        "change_a_vs_b": calc_metric_change(val_a, val_b),
    }


def rank_volatile_segments(df: pd.DataFrame, segment_col: str, metric_col: str) -> pd.DataFrame:
    """Thin wrapper for the business vocabulary over the statistical
    variance_analysis -- flags which segments are unstable candidates."""
    return variance_analysis(df, segment_col, metric_col)
