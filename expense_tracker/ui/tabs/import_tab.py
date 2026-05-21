import io

import pandas as pd
import streamlit as st

from expense_tracker.ingest.pipeline import ingest, reconcile
from expense_tracker.parsers import KNOWN_BANKS, get_parser


def render() -> None:
    st.header("Import statement")

    bank = st.selectbox("Bank", options=list(KNOWN_BANKS), index=0)
    upload = st.file_uploader("Bank statement (PDF)", type=["pdf"])
    if upload is None:
        return

    data = upload.read()
    parser = get_parser(bank)
    try:
        parsed = parser.parse(io.BytesIO(data))
    except Exception as exc:  # surface parse errors instead of crashing the app
        st.error(f"Could not parse this statement: {exc}")
        return

    st.success(
        f"Parsed {len(parsed.transactions)} transactions across "
        f"{len(parsed.accounts)} account(s), {parsed.period_start} → {parsed.period_end}."
    )
    if parsed.accounts:
        st.caption(
            "Accounts: "
            + " · ".join(
                f"{a.currency} …{a.number[-6:]} (balance {a.balance:,.2f})" for a in parsed.accounts
            )
        )

    for warning in reconcile(parsed):
        st.warning(f"Reconciliation: {warning}")

    df = pd.DataFrame(t.model_dump() for t in parsed.transactions)
    if not df.empty:
        st.dataframe(
            df[["date", "amount_native", "currency", "operation", "description"]],
            use_container_width=True, hide_index=True,
        )

    if st.button("Ingest into database", type="primary"):
        result = ingest(io.BytesIO(data), parser, upload.name)
        st.success(
            f"Inserted {result.inserted} · duplicates {result.duplicates} · "
            f"uncategorized {result.uncategorized} · needs FX {result.needs_fx}"
        )
        for warning in result.warnings:
            st.warning(warning)
