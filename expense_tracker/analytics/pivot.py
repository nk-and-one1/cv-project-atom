"""The core view: category x month pivot of summed amounts in base currency."""

import pandas as pd

from expense_tracker.db.connection import connect


def load_transactions(account_ids: list[int] | None = None) -> pd.DataFrame:
    sql = """
        SELECT t.id, t.date, t.amount_native, t.currency, t.amount_base,
               t.description, t.merchant, t.is_recurring, t.is_anomaly, t.category_id,
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
