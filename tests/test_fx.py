"""FX conversion, manual-rate storage, and repricing."""

from datetime import date

import pytest

from expense_tracker.db.connection import transaction
from expense_tracker.fx.rates import convert_to_base, list_rates, reprice, set_rate


def test_convert_same_currency_is_identity():
    assert convert_to_base(amount=1000.0, currency="KZT", on_date=date(2026, 4, 1), base="KZT") == 1000.0


def test_convert_uses_nearest_dated_rate():
    set_rate(date(2026, 1, 1), "USD", 450.0)
    set_rate(date(2026, 4, 1), "USD", 475.0)
    # 2026-03-30 is far closer to the Apr 1 rate.
    assert convert_to_base(amount=2.0, currency="USD", on_date=date(2026, 3, 30), base="KZT") == 950.0


def test_convert_missing_rate_raises():
    with pytest.raises(LookupError):
        convert_to_base(amount=1.0, currency="EUR", on_date=date(2026, 4, 1), base="KZT")


def test_set_rate_upserts_and_uppercases():
    set_rate(date(2026, 4, 1), "usd", 475.0)
    set_rate(date(2026, 4, 1), "USD", 480.0)  # same date+currency -> update
    usd = [r for r in list_rates() if r["currency"] == "USD"]
    assert len(usd) == 1
    assert usd[0]["rate_to_base"] == 480.0


def test_reprice_fills_missing_amount_base(add_tx):
    add_tx([{
        "date": "2026-04-10", "amount_native": 2.0, "currency": "USD",
        "amount_base": None, "merchant": "X", "category_id": 99,
    }])
    set_rate(date(2026, 4, 1), "USD", 475.0)
    assert reprice(base="KZT") == 1
    with transaction() as conn:
        amount_base = conn.execute("SELECT amount_base FROM transactions LIMIT 1").fetchone()["amount_base"]
    assert amount_base == 950.0
