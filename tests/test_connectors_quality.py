"""Tests for connectors.quality -- the 8 data-quality check functions."""

import pandas as pd
import pytest

from connectors import quality


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "amount": [10.0, -5.0, 20.0, None, 20.0],
            "email": ["a@x.com", "bad-email", "c@x.com", "d@x.com", "e@x.com"],
            "signup_date": ["2026-01-01", "2026-01-01", "2026-01-05", None, "2026-01-07"],
        }
    )


def test_profile_dataset_reports_per_column_stats(df):
    result = quality.profile_dataset(df)
    assert result["rows"] == 5
    amount_col = next(c for c in result["columns"] if c["name"] == "amount")
    assert amount_col["null_count"] == 1
    assert amount_col["min"] == -5.0


def test_check_missing_all_columns(df):
    result = quality.check_missing(df)
    assert result["columns"]["amount"]["null_count"] == 1
    assert result["columns"]["id"]["null_count"] == 0


def test_check_missing_single_column(df):
    result = quality.check_missing(df, column="signup_date")
    assert list(result["columns"].keys()) == ["signup_date"]
    assert result["columns"]["signup_date"]["null_count"] == 1


def test_check_duplicates_detects_repeated_rows():
    dup_df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    result = quality.check_duplicates(dup_df)
    assert result["duplicate_count"] == 1
    assert result["sample_indices"] == [1]


def test_check_invalid_values_min_max(df):
    result = quality.check_invalid_values(df, "amount", min_value=0)
    assert result["invalid_count"] == 1
    assert result["sample_values"] == [-5.0]


def test_check_invalid_values_allowed_values():
    d = pd.DataFrame({"status": ["open", "closed", "bogus"]})
    result = quality.check_invalid_values(d, "status", allowed_values=["open", "closed"])
    assert result["invalid_count"] == 1
    assert result["sample_values"] == ["bogus"]


def test_check_format_consistency_detects_dominant_pattern(df):
    result = quality.check_format_consistency(df, "email")
    assert result["dominant_pattern"] == "email"
    assert result["consistency_pct"] == 80.0


def test_check_date_coverage_reports_range_and_gaps(df):
    result = quality.check_date_coverage(df, "signup_date")
    assert result["min_date"].startswith("2026-01-01")
    assert result["max_date"].startswith("2026-01-07")
    assert result["missing_days"] > 0


def test_check_date_coverage_empty_column_handles_gracefully():
    d = pd.DataFrame({"date": [None, None]})
    result = quality.check_date_coverage(d, "date")
    assert result["min_date"] is None
    assert result["missing_days"] == 0


def test_check_schema_detects_missing_extra_and_mismatched(df):
    result = quality.check_schema(df, {"id": "int64", "amount": "int64", "missing_col": "object"})
    assert "missing_col" in result["missing_columns"]
    assert "email" in result["extra_columns"]
    assert any(m["column"] == "amount" for m in result["type_mismatches"])


def test_assess_data_quality_flags_high_missingness():
    d = pd.DataFrame({"a": [1, None, None, None]})
    result = quality.assess_data_quality(d)
    assert "high_missingness" in result["flags"]
    assert result["score"] < 100


def test_assess_data_quality_clean_data_scores_high():
    d = pd.DataFrame({"a": [1, 2, 3, 4]})
    result = quality.assess_data_quality(d)
    assert result["score"] == 100.0
    assert result["flags"] == []
