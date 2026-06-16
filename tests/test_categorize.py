"""Rules engine and correction-to-rule learning."""

import re

from expense_tracker.categorize.learn import propose_rule_from_correction, record_correction
from expense_tracker.categorize.rules import add_rule, categorize_with_rules
from expense_tracker.db.connection import transaction


def test_seed_rule_matches_netflix():
    with transaction() as conn:
        assert categorize_with_rules(conn, "NETFLIX.COM monthly", "NETFLIX") == 41  # Subscriptions


def test_no_match_returns_none():
    with transaction() as conn:
        assert categorize_with_rules(conn, "totally unknown merchant zzz", None) is None


def test_add_rule_then_match():
    with transaction() as conn:
        add_rule(conn, r"magnum", 2)  # Groceries
        assert categorize_with_rules(conn, "purchase at MAGNUM store", "MAGNUM") == 2


def test_lower_priority_wins():
    with transaction() as conn:
        conn.execute("DELETE FROM rules")
        add_rule(conn, r"shop", 31)  # default priority 100
        conn.execute("INSERT INTO rules (pattern, category_id, priority) VALUES (?, ?, ?)", (r"shop", 33, 10))
        assert categorize_with_rules(conn, "online shop", None) == 33


def test_invalid_regex_is_skipped():
    with transaction() as conn:
        conn.execute("DELETE FROM rules")
        conn.execute("INSERT INTO rules (pattern, category_id, priority) VALUES (?, ?, ?)", (r"[unclosed", 2, 10))
        add_rule(conn, r"zzqq", 4)
        assert categorize_with_rules(conn, "thing zzqq thing", None) == 4


def test_record_correction_updates_and_logs(add_tx):
    add_tx([{"date": "2026-04-10", "amount_base": -100.0, "merchant": "MAGNUM", "category_id": 99}])  # Uncategorized
    with transaction() as conn:
        tx_id = conn.execute("SELECT id FROM transactions LIMIT 1").fetchone()["id"]
        record_correction(conn, tx_id, 2)  # -> Groceries
    with transaction() as conn:
        cat = conn.execute("SELECT category_id FROM transactions WHERE id = ?", (tx_id,)).fetchone()["category_id"]
        corr = conn.execute(
            "SELECT old_category_id, new_category_id FROM corrections WHERE transaction_id = ?", (tx_id,)
        ).fetchone()
    assert cat == 2
    assert corr["old_category_id"] == 99
    assert corr["new_category_id"] == 2


def test_propose_rule_from_correction(add_tx):
    add_tx([{
        "date": "2026-04-10", "amount_base": -100.0,
        "merchant": "MAGNUM ALMATY", "description": "card purchase", "category_id": 99,
    }])
    with transaction() as conn:
        tx_id = conn.execute("SELECT id FROM transactions LIMIT 1").fetchone()["id"]
        pattern = propose_rule_from_correction(conn, tx_id)
    assert pattern == re.escape("magnum almaty")  # first two merchant tokens, lowercased


def test_propose_rule_missing_tx_returns_none():
    with transaction() as conn:
        assert propose_rule_from_correction(conn, 999999) is None
