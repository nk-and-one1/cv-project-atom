"""Claude fallback categorizer for un-ruled transactions.

Batched so we don't hit the API once per row. Output is a category name
that we map back to a category_id; if it doesn't match the taxonomy we
fall back to Uncategorized so the user can correct it.
"""

import json
import sqlite3
from dataclasses import dataclass

from expense_tracker.config import ANTHROPIC_API_KEY, LLM_MODEL


@dataclass
class LLMSuggestion:
    transaction_id: int
    category_name: str
    confidence: float


def suggest_categories(conn: sqlite3.Connection, transaction_ids: list[int]) -> list[LLMSuggestion]:
    """Ask Claude to categorize a batch of un-categorized transactions.

    Returns a suggestion per transaction. Caller decides whether to apply.
    """
    if not transaction_ids:
        return []
    if not ANTHROPIC_API_KEY:
        return []

    rows = conn.execute(
        f"SELECT id, description, merchant, amount_base FROM transactions "
        f"WHERE id IN ({','.join('?' * len(transaction_ids))})",
        transaction_ids,
    ).fetchall()

    categories = conn.execute(
        "SELECT c.name AS name, p.name AS parent "
        "FROM categories c LEFT JOIN categories p ON c.parent_id = p.id"
    ).fetchall()
    taxonomy = [f"{r['parent']} > {r['name']}" if r["parent"] else r["name"] for r in categories]

    # Build the prompt; actual Anthropic call wired up in the next iteration.
    _ = {
        "model": LLM_MODEL,
        "taxonomy": taxonomy,
        "rows": [dict(r) for r in rows],
    }
    raise NotImplementedError("Wire Anthropic client once a sample statement is loaded.")
