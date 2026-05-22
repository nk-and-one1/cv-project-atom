"""Budget vs. actual, which must match spend to budgets by category_id."""

import pandas as pd

from expense_tracker.analytics.budgets import budget_vs_actual, load_budgets
from expense_tracker.db.connection import transaction

BUDGET_COLS = ["category", "budget", "actual", "remaining", "pct_used"]


def _set_budget(category_id, amount):
    with transaction() as conn:
        conn.execute(
            "UPDATE categories SET budget_monthly_base = ? WHERE id = ?",
            (amount, category_id),
        )


def test_load_budgets_only_returns_budgeted():
    _set_budget(2, 50000)  # Groceries
    b = load_budgets()
    assert list(b["category_id"]) == [2]
    assert b.iloc[0]["name"] == "Groceries"


def test_budget_vs_actual_matches_subcategory_by_id():
    # Regression: actuals carry the full "Food > Groceries" path while budgets
    # store the leaf name "Groceries"; matching must be by category_id.
    _set_budget(2, 50000)
    tx = pd.DataFrame([
        {"date": pd.Timestamp("2026-04-10"), "category": "Food > Groceries", "category_id": 2, "amount_base": -20000.0},
        {"date": pd.Timestamp("2026-04-11"), "category": "Food > Groceries", "category_id": 2, "amount_base": -10000.0},
        # NULL category forces the category_id column to float64; merge must still match.
        {"date": pd.Timestamp("2026-04-12"), "category": "Uncategorized", "category_id": None, "amount_base": -999.0},
        # different month -> excluded.
        {"date": pd.Timestamp("2026-03-01"), "category": "Food > Groceries", "category_id": 2, "amount_base": -7777.0},
    ])
    out = budget_vs_actual(tx, "2026-04")
    row = out[out["category"] == "Groceries"].iloc[0]
    assert row["actual"] == 30000.0
    assert row["budget"] == 50000.0
    assert row["remaining"] == 20000.0
    assert row["pct_used"] == 60.0


def test_budget_vs_actual_no_spend_is_zero():
    _set_budget(4, 10000)  # Coffee, no Coffee spend below
    tx = pd.DataFrame([
        {"date": pd.Timestamp("2026-04-10"), "category": "Food > Groceries", "category_id": 2, "amount_base": -20000.0},
    ])
    out = budget_vs_actual(tx, "2026-04")
    coffee = out[out["category"] == "Coffee"].iloc[0]
    assert coffee["actual"] == 0.0
    assert coffee["pct_used"] == 0.0


def test_budget_vs_actual_empty_transactions():
    _set_budget(2, 50000)
    out = budget_vs_actual(
        pd.DataFrame(columns=["date", "category", "category_id", "amount_base"]), "2026-04"
    )
    assert out.empty
    assert list(out.columns) == BUDGET_COLS
