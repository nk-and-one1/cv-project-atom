"""Regex rules engine. Rules live in the `rules` table, lowest priority wins ties."""

import re
import sqlite3


def categorize_with_rules(conn: sqlite3.Connection, description: str, merchant: str | None) -> int | None:
    haystack = f"{merchant or ''} {description}".lower()
    rows = conn.execute(
        "SELECT pattern, category_id FROM rules ORDER BY priority ASC, id ASC"
    ).fetchall()
    for row in rows:
        try:
            if re.search(row["pattern"], haystack, flags=re.IGNORECASE):
                return row["category_id"]
        except re.error:
            continue
    return None


def add_rule(conn: sqlite3.Connection, pattern: str, category_id: int, *, from_correction: bool = False) -> int:
    cur = conn.execute(
        "INSERT INTO rules (pattern, category_id, created_from_correction) VALUES (?, ?, ?)",
        (pattern, category_id, 1 if from_correction else 0),
    )
    return cur.lastrowid
