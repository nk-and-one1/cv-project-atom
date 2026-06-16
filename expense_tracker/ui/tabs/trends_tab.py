import streamlit as st

from expense_tracker.analytics.pivot import load_transactions


def render() -> None:
    st.header("Trends")
    df = load_transactions()
    if df.empty:
        st.info("No transactions yet.")
        return

    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly_by_category = df.groupby(["month", "category"])["amount_base"].sum().unstack(fill_value=0)
    st.subheader("Monthly spend by category")
    st.line_chart(monthly_by_category)
