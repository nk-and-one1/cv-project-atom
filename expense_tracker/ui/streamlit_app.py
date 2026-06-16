"""Streamlit entry point. Run with: streamlit run expense_tracker/ui/streamlit_app.py"""

import streamlit as st

from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import init_db

st.set_page_config(page_title="Expense Tracker", layout="wide")
init_db()

st.title("Expense Tracker")
st.caption(f"Base currency: {BASE_CURRENCY}")

tab_import, tab_pivot, tab_trends, tab_insights, tab_fx, tab_rules = st.tabs(
    ["Import", "Pivot", "Trends", "Insights", "FX", "Rules"]
)

with tab_import:
    from expense_tracker.ui.tabs.import_tab import render as render_import
    render_import()

with tab_pivot:
    from expense_tracker.ui.tabs.pivot_tab import render as render_pivot
    render_pivot()

with tab_trends:
    from expense_tracker.ui.tabs.trends_tab import render as render_trends
    render_trends()

with tab_insights:
    from expense_tracker.ui.tabs.insights_tab import render as render_insights
    render_insights()

with tab_fx:
    from expense_tracker.ui.tabs.fx_tab import render as render_fx
    render_fx()

with tab_rules:
    from expense_tracker.ui.tabs.rules_tab import render as render_rules
    render_rules()
