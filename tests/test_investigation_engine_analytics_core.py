import pandas as pd
import pytest

from investigation_engine.analytics.core import (
    aggregate,
    calc_metric_change,
    filter_rows,
    group_by,
    segment,
    sort_rows,
)


@pytest.fixture
def sales_df():
    return pd.DataFrame(
        {
            "product": ["A", "A", "B", "B", "C"],
            "region": ["east", "west", "east", "west", "east"],
            "revenue": [100, 50, 200, 30, 20],
        }
    )


def test_filter_rows_eq(sales_df):
    out = filter_rows(sales_df, "product", "==", "A")
    assert len(out) == 2
    assert set(out["product"]) == {"A"}


def test_filter_rows_gt(sales_df):
    out = filter_rows(sales_df, "revenue", ">", 100)
    assert set(out["product"]) == {"B"}


def test_filter_rows_in(sales_df):
    out = filter_rows(sales_df, "product", "in", ["A", "C"])
    assert set(out["product"]) == {"A", "C"}


def test_filter_rows_unknown_column_raises(sales_df):
    with pytest.raises(KeyError):
        filter_rows(sales_df, "nope", "==", 1)


def test_sort_rows_descending(sales_df):
    out = sort_rows(sales_df, by="revenue", ascending=False)
    assert out.iloc[0]["revenue"] == 200


def test_aggregate_sum(sales_df):
    assert aggregate(sales_df, "revenue", "sum") == 400


def test_aggregate_mean(sales_df):
    assert aggregate(sales_df, "revenue", "mean") == 80


def test_group_by_sum_sorted_desc(sales_df):
    out = group_by(sales_df, "product", "revenue", "sum")
    assert list(out["product"]) == ["B", "A", "C"]
    assert out.iloc[0]["revenue"] == 230


def test_calc_metric_change_normal():
    result = calc_metric_change(72, 100)
    assert result["abs_change"] == -28
    assert result["pct_change"] == pytest.approx(-28.0)


def test_calc_metric_change_zero_previous_nonzero_current():
    result = calc_metric_change(10, 0)
    assert result["pct_change"] == float("inf")


def test_calc_metric_change_zero_previous_zero_current():
    result = calc_metric_change(0, 0)
    assert result["pct_change"] == 0.0


def test_segment_pct_of_total_sums_to_100(sales_df):
    out = segment(sales_df, "product", "revenue", "sum")
    assert abs(out["pct_of_total"].sum() - 100.0) < 1e-9
    # biggest driver first
    assert out.iloc[0]["product"] == "B"


def test_segment_top_n(sales_df):
    out = segment(sales_df, "product", "revenue", "sum", top_n=1)
    assert len(out) == 1
    assert out.iloc[0]["product"] == "B"
