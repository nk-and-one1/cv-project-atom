"""Find recurring transactions (subscriptions, rent, salary, gym, etc.)."""

import pandas as pd


def detect_recurring(df: pd.DataFrame, *, min_occurrences: int = 3, tolerance_days: int = 4) -> pd.DataFrame:
    """Cluster by normalized merchant; flag groups with regular cadence."""
    if df.empty:
        return pd.DataFrame(columns=["merchant", "cadence_days", "avg_amount", "occurrences", "last_seen"])

    df = df.copy()
    df["merchant_norm"] = df["merchant"].fillna(df["description"]).str.lower().str.strip()

    rows = []
    for merchant, group in df.groupby("merchant_norm"):
        if len(group) < min_occurrences:
            continue
        sorted_dates = group["date"].sort_values()
        intervals = sorted_dates.diff().dt.days.dropna()
        if intervals.empty:
            continue
        median_interval = intervals.median()
        if intervals.between(median_interval - tolerance_days, median_interval + tolerance_days).mean() < 0.7:
            continue
        rows.append({
            "merchant": merchant,
            "cadence_days": int(median_interval),
            "avg_amount": float(group["amount_base"].mean()),
            "occurrences": int(len(group)),
            "last_seen": group["date"].max(),
        })
    columns = ["merchant", "cadence_days", "avg_amount", "occurrences", "last_seen"]
    return pd.DataFrame(rows, columns=columns).sort_values("avg_amount", ascending=False)
