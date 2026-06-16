import sqlite3

import pandas as pd
import streamlit as st

from expense_tracker.categorize.learn import propose_rule_from_correction, record_correction
from expense_tracker.categorize.rules import add_rule, categorize_with_rules
from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import connect, transaction


def _category_options(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT c.id, COALESCE(p.name || ' > ' || c.name, c.name) AS name "
        "FROM categories c LEFT JOIN categories p ON p.id = c.parent_id "
        "WHERE c.name != 'Uncategorized' ORDER BY name"
    ).fetchall()
    return {r["name"]: r["id"] for r in rows}


def _render_uncategorized(name_to_id: dict[str, int]) -> None:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, date, COALESCE(merchant, '') AS merchant, description, "
            "amount_native, currency FROM transactions "
            "WHERE category_id IS NULL ORDER BY date DESC, id"
        ).fetchall()
    finally:
        conn.close()

    st.subheader(f"Uncategorized — {len(rows)} to sort")
    if not rows:
        st.success("All transactions are categorized.")
        return

    df = pd.DataFrame(
        {
            "id": r["id"],
            "date": r["date"],
            "description": (f"{r['merchant']} · " if r["merchant"] else "") + r["description"],
            "amount": f"{r['amount_native']:,.2f} {r['currency']}",
        }
        for r in rows
    ).set_index("id")
    df["category"] = ""

    edited = st.data_editor(
        df,
        column_config={
            "date": st.column_config.TextColumn("Date", disabled=True),
            "description": st.column_config.TextColumn("Description", width="large", disabled=True),
            "amount": st.column_config.TextColumn("Amount", disabled=True),
            "category": st.column_config.SelectboxColumn(
                "Assign category", options=[""] + list(name_to_id), required=False
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="uncat_editor",
    )

    make_rules = st.checkbox(
        "Also create rules so future imports auto-categorize similar transactions", value=False
    )

    if st.button("Apply categorizations", type="primary"):
        assignments = [(int(i), name_to_id[v]) for i, v in edited["category"].items() if v]
        if not assignments:
            st.warning("Pick a category for at least one row first.")
            return

        rules_made = swept = 0
        with transaction() as conn:
            for tx_id, cat_id in assignments:
                if make_rules:
                    pattern = propose_rule_from_correction(conn, tx_id)
                    if pattern:
                        try:
                            add_rule(conn, pattern, cat_id, from_correction=True)
                            rules_made += 1
                        except sqlite3.IntegrityError:
                            pass  # identical rule already exists
                record_correction(conn, tx_id, cat_id)

            if rules_made:
                for r in conn.execute(
                    "SELECT id, description, merchant FROM transactions WHERE category_id IS NULL"
                ).fetchall():
                    cid = categorize_with_rules(conn, r["description"], r["merchant"])
                    if cid is not None:
                        conn.execute(
                            "UPDATE transactions SET category_id = ? WHERE id = ?", (cid, r["id"])
                        )
                        swept += 1

        msg = f"Categorized {len(assignments)} transaction(s)."
        if rules_made:
            msg += f" Created {rules_made} rule(s); auto-sorted {swept} more from them."
        st.session_state["rules_flash"] = msg
        st.rerun()


def render() -> None:
    st.header("Rules and categories")

    flash = st.session_state.pop("rules_flash", None)
    if flash:
        st.success(flash)

    conn = connect()
    try:
        name_to_id = _category_options(conn)
    finally:
        conn.close()

    _render_uncategorized(name_to_id)
    st.divider()

    conn = connect()
    try:
        categories = pd.read_sql_query(
            "SELECT c.id, COALESCE(p.name || ' > ' || c.name, c.name) AS name, "
            "c.budget_monthly_base FROM categories c "
            "LEFT JOIN categories p ON p.id = c.parent_id "
            "ORDER BY name",
            conn,
        )
        rules = pd.read_sql_query(
            "SELECT r.id, r.pattern, r.priority, "
            "COALESCE(p.name || ' > ' || c.name, c.name) AS category "
            "FROM rules r "
            "JOIN categories c ON c.id = r.category_id "
            "LEFT JOIN categories p ON p.id = c.parent_id "
            "ORDER BY r.priority",
            conn,
        )
    finally:
        conn.close()

    st.subheader("Categories & budgets")
    st.caption(f"Set a monthly budget ({BASE_CURRENCY}) per category; leave blank for none. "
               "Budget vs. actual shows on the Insights tab.")
    edited_cats = st.data_editor(
        categories.set_index("id"),
        column_config={
            "name": st.column_config.TextColumn("Category", disabled=True),
            "budget_monthly_base": st.column_config.NumberColumn(
                f"Monthly budget ({BASE_CURRENCY})", min_value=0.0, step=1000.0, format="%.2f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="budget_editor",
    )
    if st.button("Save budgets"):
        with transaction() as conn:
            for cat_id, row in edited_cats.iterrows():
                val = row["budget_monthly_base"]
                conn.execute(
                    "UPDATE categories SET budget_monthly_base = ? WHERE id = ?",
                    (None if pd.isna(val) else float(val), int(cat_id)),
                )
        st.session_state["rules_flash"] = "Budgets saved."
        st.rerun()

    st.subheader("Rules")
    if rules.empty:
        st.info("No rules yet. They'll appear here as you confirm corrections.")
    else:
        st.dataframe(rules, use_container_width=True)
