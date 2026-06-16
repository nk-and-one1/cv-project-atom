import streamlit as st

from expense_tracker.analytics.pivot import income_by_month, load_transactions, spend_by_month
from expense_tracker.config import BASE_CURRENCY


def render() -> None:
    st.header("Category × month")
    df = load_transactions()
    if df.empty:
        st.info("No transactions yet. Import a statement to see the pivot.")
        return

    st.subheader("Spend by category")
    st.caption(f"Expenses shown as positive amounts, in {BASE_CURRENCY}.")
    spend = spend_by_month(df)
    if spend.empty:
        st.info("No expenses recorded yet.")
    else:
        st.dataframe(spend, use_container_width=True)

    st.subheader("Income")
    income = income_by_month(df)
    if income.empty:
        st.info("No income recorded yet.")
    else:
        st.dataframe(income, use_container_width=True)
