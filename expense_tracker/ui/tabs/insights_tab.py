import streamlit as st

from expense_tracker.analytics.anomalies import flag_anomalies
from expense_tracker.analytics.budgets import budget_vs_actual
from expense_tracker.analytics.pivot import load_transactions
from expense_tracker.analytics.recurring import detect_recurring


def render() -> None:
    st.header("Insights")
    df = load_transactions()
    if df.empty:
        st.info("No transactions yet.")
        return

    st.subheader("Top merchants")
    top = (
        df.assign(spend=df["amount_base"].abs())
        .groupby(df["merchant"].fillna(df["description"]))["spend"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    st.bar_chart(top)

    st.subheader("Recurring transactions")
    recurring = detect_recurring(df)
    st.dataframe(recurring, use_container_width=True)

    st.subheader("Anomalies")
    anomalies = flag_anomalies(df)
    st.dataframe(
        anomalies[["date", "category", "merchant", "amount_base", "anomaly_score"]]
        if not anomalies.empty else anomalies,
        use_container_width=True,
    )

    st.subheader("Budget vs actual (current month)")
    current_month = df["date"].max().strftime("%Y-%m")
    bva = budget_vs_actual(df, current_month)
    st.dataframe(bva, use_container_width=True)
