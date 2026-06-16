"""The core view: category x month pivot of summed amounts in base currency."""

import pandas as pd

from expense_tracker.db.connection import connect


def load_transactions(account_ids: list[int] | None = None) -> pd.DataFrame:
    sql = """
        SELECT t.id, t.date, t.amount_native, t.currency, t.amount_base,
               t.description, t.merchant, t.category_id,
               COALESCE(p.name || ' > ' || c.name, c.name, 'Uncategorized') AS category,
               a.name AS account
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN categories p ON p.id = c.parent_id
        LEFT JOIN accounts   a ON a.id = t.account_id
    """
    params: tuple = ()
    if account_ids:
        sql += f" WHERE t.account_id IN ({','.join('?' * len(account_ids))})"
        params = tuple(account_ids)
    sql += " ORDER BY t.date DESC"

    conn = connect()
    try:
        df = pd.read_sql_query(sql, conn, params=params, parse_dates=["date"])
    finally:
        conn.close()
    return df


def pivot_by_month(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df.pivot_table(
        index="category",
        columns="month",
        values="amount_base",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="Total",
    )


def spend_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Expense rows only (amount_base < 0), shown as positive magnitudes.

    Amounts are stored signed — expenses negative, income positive — so a
    spend view reads more naturally with the sign flipped. Unpriced rows
    (amount_base NULL) drop out, as they can't be summed in the base currency.
    """
    if df.empty:
        return df
    spend = df[df["amount_base"] < 0].copy()
    if spend.empty:
        return spend
    spend["amount_base"] = spend["amount_base"].abs()
    return pivot_by_month(spend)


def income_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Income rows only (amount_base > 0), already positive."""
    if df.empty:
        return df
    income = df[df["amount_base"] > 0].copy()
    if income.empty:
        return income
    return pivot_by_month(income)


def to_hierarchical(pv: pd.DataFrame, indent: str = " " * 4) -> pd.DataFrame:
    """Re-order a flat 'Parent > Child' pivot into a Word-style hierarchy.

    Parent rows show a rollup of (any direct parent rows + all children).
    Children are indented beneath their parent with a non-breaking-space
    prefix so the indent survives HTML rendering. A 'Total' margin row,
    if present, is preserved at the bottom.
    """
    if pv.empty:
        return pv

    total_row = pv.loc[["Total"]] if "Total" in pv.index else None
    rows = pv.drop(index="Total", errors="ignore")

    parents: dict[str, dict] = {}
    for label, row in rows.iterrows():
        if " > " in label:
            parent, child = label.split(" > ", 1)
        else:
            parent, child = label, None
        bucket = parents.setdefault(parent, {"direct": None, "children": []})
        if child is None:
            bucket["direct"] = row
        else:
            bucket["children"].append((child, row))

    labels: list[str] = []
    data: list[pd.Series] = []
    for parent in sorted(parents):
        bucket = parents[parent]
        rollup = pd.Series(0.0, index=pv.columns)
        if bucket["direct"] is not None:
            rollup = rollup.add(bucket["direct"], fill_value=0)
        for _, child_row in bucket["children"]:
            rollup = rollup.add(child_row, fill_value=0)
        labels.append(parent)
        data.append(rollup)
        if bucket["direct"] is not None and bucket["children"]:
            labels.append(f"{indent}(direct)")
            data.append(bucket["direct"])
        for child_name, child_row in sorted(bucket["children"]):
            labels.append(f"{indent}{child_name}")
            data.append(child_row)

    result = pd.DataFrame(data, index=pd.Index(labels, name=pv.index.name))
    if total_row is not None:
        result = pd.concat([result, total_row])
    return result
