import streamlit as st

from expense_tracker.analytics.pivot import load_transactions, pivot_by_month


def render() -> None:
    st.header("Category x month")
    df = load_transactions()
    if df.empty:
        st.info("No transactions yet. Import a statement to see the pivot.")
        return
    pivot = pivot_by_month(df)
    st.dataframe(pivot, use_container_width=True)
