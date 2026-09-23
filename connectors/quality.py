"""Data quality checks -- operate on an already-materialized DataFrame
(a DatasetHandle.df from registry.py). Purpose per spec.md: determine
trustworthiness for analysis, NOT auto-cleaning -- every function here
reports, none of them mutate or fix the data.
"""

from __future__ import annotations

import re

import pandas as pd


def _native(value):
    """Convert a numpy/pandas scalar to a plain JSON-safe Python value."""
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def profile_dataset(df: pd.DataFrame) -> dict:
    columns = []
    for col in df.columns:
        series = df[col]
        entry = {
            "name": col,
            "dtype": str(series.dtype),
            "null_count": int(series.isnull().sum()),
            "null_pct": round(_native(series.isnull().mean()) * 100, 2),
            "unique_count": int(series.nunique()),
            "examples": [_native(v) for v in series.dropna().head(3).tolist()],
        }
        if pd.api.types.is_numeric_dtype(series) and series.notna().any():
            entry["min"] = _native(series.min())
            entry["max"] = _native(series.max())
            entry["mean"] = round(_native(series.mean()), 4)
        columns.append(entry)
    return {"rows": len(df), "columns": columns}


def check_missing(df: pd.DataFrame, column: str | None = None) -> dict:
    cols = [column] if column else list(df.columns)
    result = {}
    for col in cols:
        series = df[col]
        null_count = int(series.isnull().sum())
        result[col] = {
            "null_count": null_count,
            "null_pct": round((null_count / len(df) * 100) if len(df) else 0.0, 2),
        }
    return {"columns": result}


def check_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> dict:
    dup_mask = df.duplicated(subset=subset, keep="first")
    dup_count = int(dup_mask.sum())
    return {
        "duplicate_count": dup_count,
        "duplicate_pct": round((dup_count / len(df) * 100) if len(df) else 0.0, 2),
        "sample_indices": df.index[dup_mask].tolist()[:5],
    }


def check_invalid_values(
    df: pd.DataFrame,
    column: str,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    allowed_values: list | None = None,
) -> dict:
    series = df[column]
    invalid_mask = pd.Series(False, index=series.index)
    if min_value is not None:
        invalid_mask |= series < min_value
    if max_value is not None:
        invalid_mask |= series > max_value
    if allowed_values is not None:
        invalid_mask |= ~series.isin(allowed_values)
    invalid_mask &= series.notna()
    invalid_count = int(invalid_mask.sum())
    return {
        "invalid_count": invalid_count,
        "invalid_pct": round((invalid_count / len(df) * 100) if len(df) else 0.0, 2),
        "sample_values": [_native(v) for v in series[invalid_mask].head(5).tolist()],
    }


_PATTERN_RULES: list[tuple[str, re.Pattern]] = [
    ("integer", re.compile(r"^-?\d+$")),
    ("decimal", re.compile(r"^-?\d+\.\d+$")),
    ("email", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
    ("date_iso", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("alpha", re.compile(r"^[A-Za-z]+$")),
]


def _classify(value: str) -> str:
    for name, pattern in _PATTERN_RULES:
        if pattern.match(value):
            return name
    return "other"


def check_format_consistency(df: pd.DataFrame, column: str) -> dict:
    series = df[column].dropna().astype(str)
    if series.empty:
        return {"dominant_pattern": None, "consistency_pct": 0.0, "pattern_counts": {}}
    labels = series.map(_classify)
    counts = labels.value_counts()
    dominant = counts.index[0]
    return {
        "dominant_pattern": dominant,
        "consistency_pct": round(counts.iloc[0] / len(labels) * 100, 2),
        "pattern_counts": {k: int(v) for k, v in counts.items()},
    }


def check_date_coverage(df: pd.DataFrame, column: str) -> dict:
    parsed = pd.to_datetime(df[column], errors="coerce")
    valid = parsed.dropna()
    if valid.empty:
        return {"min_date": None, "max_date": None, "unparseable_count": int(parsed.isna().sum()), "missing_days": 0}
    full_range = pd.date_range(valid.min().normalize(), valid.max().normalize(), freq="D")
    present_days = set(valid.dt.normalize())
    missing_days = [d for d in full_range if d not in present_days]
    return {
        "min_date": valid.min().isoformat(),
        "max_date": valid.max().isoformat(),
        "unparseable_count": int(parsed.isna().sum() - df[column].isnull().sum()),
        "missing_days": len(missing_days),
    }


def check_schema(df: pd.DataFrame, expected_schema: dict[str, str]) -> dict:
    actual_cols = set(df.columns)
    expected_cols = set(expected_schema.keys())
    mismatches = []
    for col in actual_cols & expected_cols:
        actual_type = str(df[col].dtype)
        if actual_type != expected_schema[col]:
            mismatches.append({"column": col, "expected": expected_schema[col], "actual": actual_type})
    return {
        "missing_columns": sorted(expected_cols - actual_cols),
        "extra_columns": sorted(actual_cols - expected_cols),
        "type_mismatches": mismatches,
    }


def assess_data_quality(df: pd.DataFrame) -> dict:
    """Aggregate score (0-100, higher is better) from missingness and
    duplication -- a coarse trustworthiness signal, not a substitute for
    the per-check tools above."""
    missing = check_missing(df)
    dup = check_duplicates(df)
    avg_null_pct = (
        sum(c["null_pct"] for c in missing["columns"].values()) / len(missing["columns"])
        if missing["columns"]
        else 0.0
    )
    score = round(max(0.0, 100.0 - avg_null_pct - dup["duplicate_pct"]), 2)
    flags = []
    if avg_null_pct > 10:
        flags.append("high_missingness")
    if dup["duplicate_pct"] > 5:
        flags.append("high_duplication")
    return {
        "score": score,
        "avg_null_pct": round(avg_null_pct, 2),
        "duplicate_pct": dup["duplicate_pct"],
        "flags": flags,
    }
