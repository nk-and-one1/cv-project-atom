import datetime as dt

import pandas as pd
import streamlit as st

from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import connect
from expense_tracker.fx.rates import list_rates, reprice, set_rate


def _awaiting_fx() -> list[dict]:
    conn = connect()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT currency, COUNT(*) AS n FROM transactions "
                "WHERE amount_base IS NULL AND currency != ? GROUP BY currency",
                (BASE_CURRENCY,),
            )
        ]
    finally:
        conn.close()


def render() -> None:
    st.header(f"FX rates — base {BASE_CURRENCY}")
    st.caption("Manual mode: enter rates as 1 foreign unit = N base units. Lookups use the nearest date.")

    awaiting = _awaiting_fx()
    if awaiting:
        st.warning("Awaiting a rate: " + ", ".join(f"{m['n']} × {m['currency']}" for m in awaiting))
    else:
        st.success("All transactions are priced in the base currency.")

    st.subheader("Add or update a rate")
    default_ccy = awaiting[0]["currency"] if awaiting else "USD"
    with st.form("add_rate", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        on_date = col1.date_input("Date", value=dt.date.today())
        currency = col2.text_input("Currency (ISO)", value=default_ccy).strip().upper()
        rate = col3.number_input(
            f"1 unit = ? {BASE_CURRENCY}", min_value=0.0, value=0.0, step=0.01, format="%.6f"
        )
        submitted = st.form_submit_button("Save rate")
    if submitted:
        if currency and rate > 0:
            set_rate(on_date, currency, rate)
            st.success(f"Saved: 1 {currency} = {rate:,.6f} {BASE_CURRENCY} on {on_date}")
        else:
            st.error("Enter a currency and a rate greater than 0.")

    if st.button("Reprice transactions awaiting FX", type="primary"):
        st.success(f"Repriced {reprice(only_missing=True)} transaction(s).")

    st.subheader("Stored rates")
    rates = list_rates()
    if rates:
        st.dataframe(pd.DataFrame(rates), use_container_width=True, hide_index=True)
    else:
        st.info("No rates yet — add one above.")
