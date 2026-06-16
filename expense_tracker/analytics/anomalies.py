"""Flag transactions that are unusually large for their category."""

import pandas as pd


def flag_anomalies(df: pd.DataFrame, *, iqr_multiplier: float = 3.0) -> pd.DataFrame:
    """Per-category IQR outlier detection. Returns flagged rows with scores."""
    if df.empty:
        return df.assign(anomaly_score=[])

    df = df.copy()
    df["anomaly_score"] = 0.0
    for category, group in df.groupby("category"):
        amounts = group["amount_base"].abs()
        if len(amounts) < 5:
            continue
        q1, q3 = amounts.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        threshold = q3 + iqr_multiplier * iqr
        score = (amounts - threshold) / iqr
        df.loc[group.index, "anomaly_score"] = score.where(score > 0, 0)

    return df[df["anomaly_score"] > 0].sort_values("anomaly_score", ascending=False)
