import streamlit as st


def render() -> None:
    st.header("Import statement")
    st.write(
        "Drop a CSV or PDF below. The parser is wired up once the first bank's "
        "sample is loaded — see `expense_tracker/parsers/csv/kaspi.py`."
    )
    st.file_uploader("Bank statement", type=["csv", "pdf"], accept_multiple_files=False)
    st.selectbox("Bank", options=["kaspi"], index=0)
    st.button("Parse and preview", disabled=True, help="Wire up parser first.")
