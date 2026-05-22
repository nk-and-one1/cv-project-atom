"""Pure-DataFrame analytics: recurring detection, anomalies, monthly pivot."""

import pandas as pd

from expense_tracker.analytics.anomalies import flag_anomalies
from expense_tracker.analytics.pivot import pivot_by_month
from expense_tracker.analytics.recurring import detect_recurring

RECURRING_COLS = ["merchant", "cadence_days", "avg_amount", "occurrences", "last_seen"]


def _df(records):
    return pd.DataFrame(records)


# --- recurring -------------------------------------------------------------

def test_detect_recurring_empty_input():
    out = detect_recurring(pd.DataFrame(columns=["date", "merchant", "description", "amount_base"]))
    assert out.empty
    assert list(out.columns) == RECURRING_COLS


def test_detect_recurring_no_groups_meet_minimum():
    # Regression: previously raised KeyError('avg_amount') when nothing recurred.
    df = _df([
        {"date": pd.Timestamp("2026-01-01"), "merchant": "A", "description": "a", "amount_base": -100.0},
        {"date": pd.Timestamp("2026-01-05"), "merchant": "B", "description": "b", "amount_base": -200.0},
        {"date": pd.Timestamp("2026-01-09"), "merchant": "C", "description": "c", "amount_base": -300.0},
    ])
    out = detect_recurring(df)
    assert out.empty
    assert list(out.columns) == RECURRING_COLS


def test_detect_recurring_irregular_cadence_excluded():
    # Same merchant 3x but wildly irregular spacing -> not recurring, no crash.
    df = _df([
        {"date": pd.Timestamp("2026-01-01"), "merchant": "SHOP", "description": "x", "amount_base": -10.0},
        {"date": pd.Timestamp("2026-01-02"), "merchant": "SHOP", "description": "x", "amount_base": -10.0},
        {"date": pd.Timestamp("2026-06-01"), "merchant": "SHOP", "description": "x", "amount_base": -10.0},
    ])
    out = detect_recurring(df)
    assert out.empty
    assert list(out.columns) == RECURRING_COLS


def test_detect_recurring_monthly_merchant():
    df = _df([
        {"date": pd.Timestamp("2026-01-01"), "merchant": "NETFLIX", "description": "sub", "amount_base": -4990.0},
        {"date": pd.Timestamp("2026-01-31"), "merchant": "NETFLIX", "description": "sub", "amount_base": -4990.0},
        {"date": pd.Timestamp("2026-03-02"), "merchant": "NETFLIX", "description": "sub", "amount_base": -4990.0},
    ])
    out = detect_recurring(df)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["merchant"] == "netflix"  # normalized (lowercased) merchant
    assert row["occurrences"] == 3
    assert 28 <= row["cadence_days"] <= 32
    assert row["avg_amount"] == -4990.0


def test_detect_recurring_respects_min_occurrences():
    df = _df([
        {"date": pd.Timestamp("2026-01-01"), "merchant": "GYM", "description": "x", "amount_base": -5000.0},
        {"date": pd.Timestamp("2026-02-01"), "merchant": "GYM", "description": "x", "amount_base": -5000.0},
    ])
    assert detect_recurring(df).empty  # 2 < default min 3


# --- anomalies -------------------------------------------------------------

def test_flag_anomalies_empty():
    out = flag_anomalies(pd.DataFrame(columns=["category", "amount_base"]))
    assert out.empty
    assert "anomaly_score" in out.columns


def test_flag_anomalies_needs_min_five_per_category():
    df = _df([{"category": "Food", "amount_base": -a} for a in (1, 2, 3, 1000)])
    assert flag_anomalies(df).empty  # only 4 rows in the category


def test_flag_anomalies_flags_clear_outlier():
    amounts = [100, 110, 90, 105, 95, 100000]
    df = _df([{"category": "Food", "amount_base": -a} for a in amounts])
    out = flag_anomalies(df)
    assert len(out) == 1
    assert out.iloc[0]["amount_base"] == -100000
    assert out.iloc[0]["anomaly_score"] > 0


# --- pivot -----------------------------------------------------------------

def test_pivot_by_month_empty():
    assert pivot_by_month(pd.DataFrame(columns=["date", "category", "amount_base"])).empty


def test_pivot_by_month_sums_with_totals():
    df = _df([
        {"date": pd.Timestamp("2026-01-10"), "category": "Food > Groceries", "amount_base": -100.0},
        {"date": pd.Timestamp("2026-01-20"), "category": "Food > Groceries", "amount_base": -50.0},
        {"date": pd.Timestamp("2026-02-05"), "category": "Transport > Taxi", "amount_base": -30.0},
    ])
    pv = pivot_by_month(df)
    assert pv.loc["Food > Groceries", "2026-01"] == -150.0
    assert "Total" in pv.index
    assert "Total" in pv.columns
