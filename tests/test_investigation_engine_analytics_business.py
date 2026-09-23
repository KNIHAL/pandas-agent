import pandas as pd
import pytest

from investigation_engine.analytics.business import (
    compare_segments,
    contribution_analysis,
    driver_analysis,
    rank_volatile_segments,
)


@pytest.fixture
def current_df():
    return pd.DataFrame(
        {
            "product": ["A", "A", "B", "B", "C"],
            "revenue": [80, 40, 150, 20, 15],  # totals: A=120, B=170, C=15 -> 305
        }
    )


@pytest.fixture
def previous_df():
    return pd.DataFrame(
        {
            "product": ["A", "A", "B", "B", "C"],
            "revenue": [100, 50, 200, 30, 20],  # totals: A=150, B=230, C=20 -> 400
        }
    )


def test_contribution_analysis_ranks_by_size(current_df):
    out = contribution_analysis(current_df, "product", "revenue")
    assert list(out["product"]) == ["B", "A", "C"]
    assert abs(out["pct_of_total"].sum() - 100.0) < 1e-9


def test_driver_analysis_identifies_biggest_negative_driver(current_df, previous_df):
    out = driver_analysis(current_df, previous_df, "product", "revenue")
    # total change: A -30, B -60, C -5 => total -95
    assert out.iloc[0]["product"] == "B"
    assert out.iloc[0]["abs_change"] == -60
    contribution_sum = out["contribution_to_total_change_pct"].sum()
    assert abs(contribution_sum - 100.0) < 1e-6


def test_driver_analysis_handles_new_segment_in_current_only():
    current = pd.DataFrame({"seg": ["X", "Y"], "rev": [10, 5]})
    previous = pd.DataFrame({"seg": ["X"], "rev": [10]})
    out = driver_analysis(current, previous, "seg", "rev")
    y_row = out[out["seg"] == "Y"].iloc[0]
    assert y_row["previous"] == 0.0
    assert y_row["current"] == 5.0


def test_compare_segments_head_to_head(current_df):
    result = compare_segments(current_df, "product", "revenue", "B", "C")
    assert result["diff"] == 170 - 15
    assert result["change_a_vs_b"]["current"] == 170


def test_rank_volatile_segments_returns_dataframe(current_df):
    out = rank_volatile_segments(current_df, "product", "revenue")
    assert "coefficient_of_variation" in out.columns
    assert len(out) == 3
