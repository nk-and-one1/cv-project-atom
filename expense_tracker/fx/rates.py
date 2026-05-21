"""FX conversion to the base currency (manual-rate mode).

Rates are entered by the user and cached in the ``fx_rates`` table, where
``rate_to_base`` means "units of the base currency per 1 unit of the foreign
currency" (e.g. base KZT, currency USD, rate 475.0 -> 1 USD = 475 KZT).

Lookups pick the rate with the closest date, so a single entered rate sensibly
covers nearby transactions (handy for weekends/gaps). No network is used.
"""

from datetime import date

from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import connect


def convert_to_base(*, amount: float, currency: str, on_date: date, base: str) -> float:
    if currency == base:
        return amount
    return amount * _lookup_rate(currency, on_date)


def _lookup_rate(currency: str, on_date: date) -> float:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT rate_to_base FROM fx_rates WHERE currency = ? "
            "ORDER BY ABS(julianday(date) - julianday(?)) ASC LIMIT 1",
            (currency, on_date.isoformat()),
        ).fetchone()
        if row:
            return row["rate_to_base"]
        raise LookupError(f"No FX rate for {currency} near {on_date}")
    finally:
        conn.close()


def set_rate(on_date: date, currency: str, rate_to_base: float) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO fx_rates (date, currency, rate_to_base) VALUES (?, ?, ?) "
            "ON CONFLICT(date, currency) DO UPDATE SET rate_to_base = excluded.rate_to_base",
            (on_date.isoformat(), currency.upper(), float(rate_to_base)),
        )
        conn.commit()
    finally:
        conn.close()


def list_rates() -> list[dict]:
    conn = connect()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT date, currency, rate_to_base FROM fx_rates ORDER BY date DESC, currency"
            )
        ]
    finally:
        conn.close()


def reprice(base: str = BASE_CURRENCY, only_missing: bool = True) -> int:
    """Recompute amount_base for foreign-currency transactions from cached rates.

    By default only fills rows left unpriced at ingest (amount_base IS NULL).
    Returns the number of rows updated.
    """
    conn = connect()
    try:
        by_ccy: dict[str, list[tuple[date, float]]] = {}
        for r in conn.execute("SELECT date, currency, rate_to_base FROM fx_rates"):
            by_ccy.setdefault(r["currency"], []).append((date.fromisoformat(r["date"]), r["rate_to_base"]))

        query = "SELECT id, amount_native, currency, date FROM transactions WHERE currency != ?"
        if only_missing:
            query += " AND amount_base IS NULL"

        updated = 0
        for r in conn.execute(query, (base,)).fetchall():
            candidates = by_ccy.get(r["currency"])
            if not candidates:
                continue
            tx_date = date.fromisoformat(r["date"])
            _, rate = min(candidates, key=lambda dr: abs((dr[0] - tx_date).days))
            conn.execute(
                "UPDATE transactions SET amount_base = ? WHERE id = ?",
                (r["amount_native"] * rate, r["id"]),
            )
            updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()
