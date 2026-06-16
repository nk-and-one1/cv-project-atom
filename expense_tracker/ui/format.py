"""Shared display formatting so amounts read the same across every tab.

Display tables (``st.dataframe``) are wrapped in a pandas Styler whose money
columns carry a thousands separator; the underlying values stay numeric so the
grid still sorts by magnitude. Editable grids (``st.data_editor``) can't take a
Styler, so they format money via ``NumberColumn(format=MONEY_COLUMN_FORMAT)``.
"""

import pandas as pd
from pandas.io.formats.style import Styler

MONEY = "{:,.2f}"
RATE = "{:,.6f}"
#: NumberColumn preset for editable money columns (grouping + 2 decimals).
MONEY_COLUMN_FORMAT = "accounting"


def style(df: pd.DataFrame, formats: dict[str, str]) -> Styler:
    """Style only the named columns that are actually present in ``df``."""
    present = {col: fmt for col, fmt in formats.items() if col in df.columns}
    return df.style.format(present, na_rep="")


def money(df: pd.DataFrame, columns) -> Styler:
    """Thousands separator + 2 decimals on the given money ``columns``."""
    return style(df, {col: MONEY for col in columns})


def money_pivot(pv: pd.DataFrame) -> Styler:
    """Thousands separator on every column of a pivot (all columns are money)."""
    return pv.style.format(MONEY, na_rep="")
