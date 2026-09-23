"""Time-series analytical ops: period comparison, % change, trend
detection, anomaly detection.
"""
from __future__ import annotations

import pandas as pd

from investigation_engine.analytics.core import calc_metric_change


def period_comparison(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    current_start,
    current_end,
    previous_start,
    previous_end,
    agg: str = "sum",
) -> dict:
    """Compare an aggregated metric between two date ranges."""
    dates = pd.to_datetime(df[date_col])
    current_mask = (dates >= pd.Timestamp(current_start)) & (dates <= pd.Timestamp(current_end))
    previous_mask = (dates >= pd.Timestamp(previous_start)) & (dates <= pd.Timestamp(previous_end))

    current_val = float(getattr(df.loc[current_mask, metric_col], agg)()) if current_mask.any() else 0.0
    previous_val = float(getattr(df.loc[previous_mask, metric_col], agg)()) if previous_mask.any() else 0.0

    return calc_metric_change(current_val, previous_val)


def trend(df: pd.DataFrame, date_col: str, metric_col: str, freq: str = "D") -> pd.DataFrame:
    """Resample a metric over time and compute period-over-period % change.
    freq: pandas offset alias, e.g. 'D', 'W', 'M'."""
    ts = df[[date_col, metric_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col])
    ts = ts.set_index(date_col).resample(freq)[metric_col].sum().reset_index()
    ts["pct_change"] = ts[metric_col].pct_change() * 100.0
    return ts


def detect_anomalies(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    freq: str = "D",
    z_threshold: float = 2.0,
) -> pd.DataFrame:
    """Flag periods whose metric value is z_threshold+ std devs from the
    series mean. Simple, explainable anomaly detection -- not a full
    seasonal model, sufficient for surfacing candidate anomalies for the
    agent to investigate further."""
    ts = df[[date_col, metric_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col])
    resampled = ts.set_index(date_col).resample(freq)[metric_col].sum().reset_index()

    mean = resampled[metric_col].mean()
    std = resampled[metric_col].std()
    if not std or pd.isna(std):
        resampled["z_score"] = 0.0
    else:
        resampled["z_score"] = (resampled[metric_col] - mean) / std
    resampled["is_anomaly"] = resampled["z_score"].abs() >= z_threshold
    return resampled
