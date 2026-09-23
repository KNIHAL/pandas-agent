"""Statistical analytical ops: distribution, correlation, percentile,
variance analysis.
"""
from __future__ import annotations

import pandas as pd


def distribution(df: pd.DataFrame, column: str) -> dict:
    """Summary distribution stats for a numeric column."""
    s = df[column].dropna()
    if s.empty:
        return {"count": 0}
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "std": float(s.std()) if s.count() > 1 else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "median": float(s.median()),
        "skew": float(s.skew()) if s.count() > 2 else 0.0,
    }


def percentile(df: pd.DataFrame, column: str, q: float) -> float:
    """Value at percentile q (0-100) of a numeric column."""
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    return float(df[column].dropna().quantile(q / 100.0))


def correlation(df: pd.DataFrame, col_a: str, col_b: str, method: str = "pearson") -> float:
    """Correlation coefficient between two numeric columns."""
    paired = df[[col_a, col_b]].dropna()
    if len(paired) < 2:
        return float("nan")
    return float(paired[col_a].corr(paired[col_b], method=method))


def variance_analysis(df: pd.DataFrame, group_col: str, metric_col: str) -> pd.DataFrame:
    """Per-group variance/std of a metric -- flags which segments are
    volatile vs. stable, useful when ruling in/out a driver."""
    grouped = df.groupby(group_col, dropna=False)[metric_col].agg(
        mean="mean", std="std", count="count"
    ).reset_index()
    grouped["std"] = grouped["std"].fillna(0.0)
    grouped["coefficient_of_variation"] = grouped.apply(
        lambda r: (r["std"] / r["mean"]) if r["mean"] not in (0, None) else 0.0, axis=1
    )
    return grouped.sort_values(by="coefficient_of_variation", ascending=False).reset_index(drop=True)
