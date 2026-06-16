"""Promote user corrections into reusable rules."""

import re
import sqlite3


def record_correction(conn: sqlite3.Connection, transaction_id: int, new_category_id: int) -> None:
    old = conn.execute(
        "SELECT category_id FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    conn.execute(
        "UPDATE transactions SET category_id = ? WHERE id = ?",
        (new_category_id, transaction_id),
    )
    conn.execute(
        "INSERT INTO corrections (transaction_id, old_category_id, new_category_id) VALUES (?, ?, ?)",
        (transaction_id, old["category_id"] if old else None, new_category_id),
    )


def propose_rule_from_correction(conn: sqlite3.Connection, transaction_id: int) -> str | None:
    row = conn.execute(
        "SELECT merchant, description FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    if not row:
        return None
    token = (row["merchant"] or row["description"] or "").strip().split()[:2]
    if not token:
        return None
    return re.escape(" ".join(token).lower())
