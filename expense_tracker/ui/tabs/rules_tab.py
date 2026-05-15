import pandas as pd
import streamlit as st

from expense_tracker.db.connection import connect


def render() -> None:
    st.header("Rules and categories")

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

    st.subheader("Categories")
    st.dataframe(categories, use_container_width=True)

    st.subheader("Rules")
    if rules.empty:
        st.info("No rules yet. They'll appear here as you confirm corrections.")
    else:
        st.dataframe(rules, use_container_width=True)
