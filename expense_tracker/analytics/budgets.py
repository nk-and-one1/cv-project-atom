"""Budget vs actual comparison per category per month."""

import pandas as pd

from expense_tracker.db.connection import connect


def load_budgets() -> pd.DataFrame:
    conn = connect()
    try:
        return pd.read_sql_query(
            "SELECT id AS category_id, name, budget_monthly_base FROM categories "
            "WHERE budget_monthly_base IS NOT NULL",
            conn,
        )
    finally:
        conn.close()


def budget_vs_actual(transactions: pd.DataFrame, month: str) -> pd.DataFrame:
    """`month` is 'YYYY-MM'. Returns one row per budgeted category."""
    budgets = load_budgets()
    if budgets.empty or transactions.empty:
        return pd.DataFrame(columns=["category", "budget", "actual", "remaining", "pct_used"])

    df = transactions.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    actuals = (
        df[df["month"] == month]
        .groupby("category")["amount_base"]
        .sum()
        .abs()
        .rename("actual")
    )
    out = budgets.rename(columns={"name": "category", "budget_monthly_base": "budget"}).merge(
        actuals, on="category", how="left"
    ).fillna({"actual": 0.0})
    out["remaining"] = out["budget"] - out["actual"]
    out["pct_used"] = (out["actual"] / out["budget"] * 100).round(1)
    return out[["category", "budget", "actual", "remaining", "pct_used"]]
