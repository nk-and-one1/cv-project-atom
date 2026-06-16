"""Shared fixtures: an isolated temp database and helpers for inserting rows.

The data dir is redirected to a throwaway location *before* importing anything
that reads config, because ``expense_tracker.config`` resolves ``DB_PATH`` at
import time.
"""

import os
import tempfile

os.environ["EXPENSE_TRACKER_DATA_DIR"] = tempfile.mkdtemp(prefix="expense-tracker-tests-")
os.environ["EXPENSE_TRACKER_BASE_CURRENCY"] = "KZT"

import pytest  # noqa: E402

from expense_tracker.config import DB_PATH  # noqa: E402
from expense_tracker.db.connection import init_db, transaction  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate schema + seed before every test so cases stay isolated."""
    for f in DB_PATH.parent.glob(DB_PATH.name + "*"):
        f.unlink()
    init_db()
    yield


@pytest.fixture
def add_account():
    def _add(name="Test", bank="TestBank", currency="KZT", number="ACC-1"):
        with transaction() as conn:
            cur = conn.execute(
                "INSERT INTO accounts (name, bank, currency, number) VALUES (?, ?, ?, ?)",
                (name, bank, currency, number),
            )
            return cur.lastrowid

    return _add


@pytest.fixture
def add_tx(add_account):
    """Insert transactions, creating a default account on first use.

    Each row is a dict; missing fields get sensible defaults. Returns the
    account id the rows were written to.
    """
    state = {"account_id": None, "n": 0}

    def _add(rows, *, account_id=None):
        if account_id is None:
            if state["account_id"] is None:
                state["account_id"] = add_account()
            account_id = state["account_id"]
        with transaction() as conn:
            for r in rows:
                state["n"] += 1
                amount_native = r.get("amount_native", r.get("amount_base") or 0.0)
                conn.execute(
                    "INSERT INTO transactions "
                    "(account_id, date, amount_native, currency, amount_base, "
                    " description, merchant, category_id, dedup_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        account_id,
                        r["date"],
                        amount_native,
                        r.get("currency", "KZT"),
                        r.get("amount_base"),
                        r.get("description", r.get("merchant", "tx")),
                        r.get("merchant"),
                        r.get("category_id"),
                        r.get("dedup_hash", f"hash-{state['n']}"),
                    ),
                )
        return account_id

    return _add
