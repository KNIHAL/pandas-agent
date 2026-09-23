"""Core analytical ops: aggregation, grouping, filtering, sorting,
metric calculation, segmentation.

All functions take/return plain pandas DataFrames or simple scalars/
dicts -- callers (tools layer) are responsible for turning results
into the small structured objects passed to the agent (per spec:
"never raw rows").
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

AggFunc = Literal["sum", "mean", "count", "min", "max", "median", "std", "nunique"]
FilterOp = Literal["==", "!=", ">", ">=", "<", "<=", "in", "not in", "contains"]


def filter_rows(df: pd.DataFrame, column: str, op: FilterOp, value: Any) -> pd.DataFrame:
    """Filter rows by a single condition."""
    if column not in df.columns:
        raise KeyError(f"Unknown column: {column}")

    series = df[column]
    if op == "==":
        mask = series == value
    elif op == "!=":
        mask = series != value
    elif op == ">":
        mask = series > value
    elif op == ">=":
        mask = series >= value
    elif op == "<":
        mask = series < value
    elif op == "<=":
        mask = series <= value
    elif op == "in":
        mask = series.isin(value)
    elif op == "not in":
        mask = ~series.isin(value)
    elif op == "contains":
        mask = series.astype(str).str.contains(str(value), na=False)
    else:
        raise ValueError(f"Unsupported filter op: {op}")

    return df[mask]


def sort_rows(df: pd.DataFrame, by, ascending: bool = True) -> pd.DataFrame:
    """Sort rows by one or more columns."""
    return df.sort_values(by=by, ascending=ascending)


def aggregate(df: pd.DataFrame, column: str, func: AggFunc) -> float:
    """Compute a single aggregate metric over a column."""
    if column not in df.columns:
        raise KeyError(f"Unknown column: {column}")
    result = getattr(df[column], func)()
    return float(result) if pd.notna(result) else float("nan")


def group_by(
    df: pd.DataFrame,
    group_cols,
    metric_col: str,
    func: AggFunc = "sum",
) -> pd.DataFrame:
    """Group rows and aggregate a metric column. Returns a tidy DataFrame."""
    grouped = df.groupby(group_cols, dropna=False)[metric_col].agg(func).reset_index()
    return grouped.sort_values(by=metric_col, ascending=False).reset_index(drop=True)


def calc_metric_change(current: float, previous: float) -> dict:
    """Absolute and percentage change between two metric values."""
    abs_change = current - previous
    if previous == 0:
        pct_change = float("inf") if current != 0 else 0.0
    else:
        pct_change = (abs_change / previous) * 100.0
    return {
        "current": current,
        "previous": previous,
        "abs_change": abs_change,
        "pct_change": pct_change,
    }


def segment(
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    func: AggFunc = "sum",
    top_n=None,
) -> pd.DataFrame:
    """Segment rows by a categorical column and compute each segment's
    metric plus its % contribution to the total. Used to rank candidate
    drivers (spec step 4: break metric into candidate drivers)."""
    grouped = group_by(df, segment_col, metric_col, func)
    total = grouped[metric_col].sum()
    grouped["pct_of_total"] = (grouped[metric_col] / total * 100.0) if total else 0.0
    if top_n is not None:
        grouped = grouped.head(top_n)
    return grouped.reset_index(drop=True)
