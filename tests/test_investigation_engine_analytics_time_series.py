import pandas as pd
import pytest

from investigation_engine.analytics.time_series import (
    detect_anomalies,
    period_comparison,
    trend,
)


@pytest.fixture
def daily_df():
    dates = pd.date_range("2026-08-01", periods=10, freq="D")
    revenue = [100, 105, 98, 102, 99, 101, 100, 97, 103, 100]
    return pd.DataFrame({"date": dates, "revenue": revenue})


def test_period_comparison_change(daily_df):
    result = period_comparison(
        daily_df, "date", "revenue",
        current_start="2026-08-06", current_end="2026-08-10",
        previous_start="2026-08-01", previous_end="2026-08-05",
    )
    expected_current = daily_df.iloc[5:10]["revenue"].sum()
    expected_previous = daily_df.iloc[0:5]["revenue"].sum()
    assert result["current"] == expected_current
    assert result["previous"] == expected_previous


def test_period_comparison_no_rows_in_range_returns_zero(daily_df):
    result = period_comparison(
        daily_df, "date", "revenue",
        current_start="2027-01-01", current_end="2027-01-05",
        previous_start="2026-08-01", previous_end="2026-08-05",
    )
    assert result["current"] == 0.0


def test_trend_computes_pct_change(daily_df):
    out = trend(daily_df, "date", "revenue", freq="D")
    assert len(out) == 10
    assert pd.isna(out.iloc[0]["pct_change"])
    assert out.iloc[1]["pct_change"] == pytest.approx(5.0)


def test_detect_anomalies_flags_outlier():
    dates = pd.date_range("2026-08-01", periods=7, freq="D")
    revenue = [100, 102, 98, 101, 99, 100, 500]  # last value is an outlier
    df = pd.DataFrame({"date": dates, "revenue": revenue})
    out = detect_anomalies(df, "date", "revenue", freq="D", z_threshold=2.0)
    assert out.iloc[-1]["is_anomaly"] == True  # noqa: E712
    assert out.iloc[0]["is_anomaly"] == False  # noqa: E712


def test_detect_anomalies_flat_series_no_false_positives():
    dates = pd.date_range("2026-08-01", periods=5, freq="D")
    df = pd.DataFrame({"date": dates, "revenue": [100, 100, 100, 100, 100]})
    out = detect_anomalies(df, "date", "revenue", freq="D")
    assert not out["is_anomaly"].any()
