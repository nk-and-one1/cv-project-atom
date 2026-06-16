"""Display formatters: money columns must carry a thousands separator."""

import pandas as pd

from expense_tracker.ui.format import RATE, money, money_pivot, style


def test_money_adds_thousands_separator():
    df = pd.DataFrame({"amount": [1234567.5], "note": ["x"]})
    html = money(df, ["amount"]).to_html()
    assert "1,234,567.50" in html
    assert "x" in html  # untouched column still rendered


def test_money_ignores_absent_columns():
    df = pd.DataFrame({"amount": [1000.0]})
    # Asking for a column that isn't there must not raise.
    html = money(df, ["amount", "nope"]).to_html()
    assert "1,000.00" in html


def test_money_pivot_formats_every_column():
    pv = pd.DataFrame({"2026-01": [1500000.0], "Total": [1500000.0]}, index=["Food"])
    html = money_pivot(pv).to_html()
    assert html.count("1,500,000.00") >= 2


def test_style_respects_custom_rate_format():
    df = pd.DataFrame({"rate_to_base": [4750.123456]})
    html = style(df, {"rate_to_base": RATE}).to_html()
    assert "4,750.123456" in html
