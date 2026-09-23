import math

import pandas as pd
import pytest

from investigation_engine.analytics.statistical import (
    correlation,
    distribution,
    percentile,
    variance_analysis,
)


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "segment": ["A", "A", "A", "B", "B", "B"],
            "revenue": [100, 110, 90, 500, 50, 450],
            "units": [10, 11, 9, 50, 5, 45],
        }
    )


def test_distribution_basic_stats(df):
    d = distribution(df, "revenue")
    assert d["count"] == 6
    assert d["min"] == 50
    assert d["max"] == 500
    assert d["mean"] == pytest.approx(216.666, rel=1e-3)


def test_distribution_empty_column_returns_zero_count():
    empty = pd.DataFrame({"x": pd.Series(dtype=float)})
    d = distribution(empty, "x")
    assert d["count"] == 0


def test_percentile_median_equals_p50(df):
    p50 = percentile(df, "revenue", 50)
    assert p50 == df["revenue"].median()


def test_percentile_out_of_range_raises(df):
    with pytest.raises(ValueError):
        percentile(df, "revenue", 150)


def test_correlation_strong_positive(df):
    r = correlation(df, "revenue", "units")
    assert r > 0.99


def test_correlation_insufficient_data_returns_nan():
    df2 = pd.DataFrame({"a": [1], "b": [2]})
    r = correlation(df2, "a", "b")
    assert math.isnan(r)


def test_variance_analysis_segments_sorted_by_volatility(df):
    out = variance_analysis(df, "segment", "revenue")
    assert set(out["segment"]) == {"A", "B"}
    # B has much higher spread relative to mean than A
    assert out.iloc[0]["segment"] == "B"
