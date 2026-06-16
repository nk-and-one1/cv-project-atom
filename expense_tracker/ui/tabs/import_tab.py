import io

import pandas as pd
import streamlit as st

from expense_tracker.ingest.pipeline import ingest, reconcile
from expense_tracker.parsers import KNOWN_BANKS, get_parser


def _format_accounts(accounts) -> str:
    """One-line account summary. Tolerates a missing balance."""
    parts = []
    for a in accounts:
        tail = a.number[-6:] if a.number else "?"
        balance = f" (balance {a.balance:,.2f})" if a.balance is not None else ""
        parts.append(f"{a.currency} …{tail}{balance}")
    return " · ".join(parts)


def _format_summary(parsed) -> str:
    if parsed.period_start and parsed.period_end:
        period = f"{parsed.period_start} → {parsed.period_end}"
    else:
        period = "period unknown"
    return (
        f"Parsed {len(parsed.transactions)} transactions across "
        f"{len(parsed.accounts)} account(s), {period}."
    )


def render() -> None:
    st.header("Import statement")

    bank = st.selectbox("Bank", options=list(KNOWN_BANKS), index=0)
    upload = st.file_uploader("Bank statement (PDF)", type=["pdf"])
    if upload is None:
        return

    data = upload.read()
    if not data:
        st.error("That file is empty. Re-export the statement and try again.")
        return

    parser = get_parser(bank)
    try:
        parsed = parser.parse(io.BytesIO(data))
    except Exception as exc:  # surface parse errors instead of crashing the app
        st.error(f"Could not parse this statement: {exc}")
        return

    if not parsed.transactions:
        st.warning(
            f"No transactions found in this file. Check that the bank is right "
            f"(selected: {bank}) and that this is a statement PDF."
        )
        return

    st.success(_format_summary(parsed))
    if parsed.accounts:
        st.caption("Accounts: " + _format_accounts(parsed.accounts))

    for warning in reconcile(parsed):
        st.warning(f"Reconciliation: {warning}")

    df = pd.DataFrame(t.model_dump() for t in parsed.transactions)
    st.dataframe(
        df[["date", "amount_native", "currency", "operation", "description"]],
        use_container_width=True, hide_index=True,
    )

    if st.button("Ingest into database", type="primary"):
        try:
            result = ingest(io.BytesIO(data), parser, upload.name)
        except Exception as exc:  # don't dump a traceback on the primary action
            st.error(f"Import failed: {exc}")
            return
        st.success(
            f"Inserted {result.inserted} · duplicates {result.duplicates} · "
            f"uncategorized {result.uncategorized} · needs FX {result.needs_fx}"
        )
        for warning in result.warnings:
            st.warning(warning)
