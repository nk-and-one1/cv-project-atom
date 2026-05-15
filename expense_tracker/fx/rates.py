"""FX conversion to the base currency (KZT by default).

Daily rates are cached in the fx_rates table. The fetcher is left as a stub
until you pick a source — exchangerate.host (free) and the National Bank of
Kazakhstan public API are both reasonable choices.
"""

from datetime import date

from expense_tracker.db.connection import connect


def convert_to_base(*, amount: float, currency: str, on_date: date, base: str) -> float:
    if currency == base:
        return amount
    rate = _lookup_rate(currency, on_date, base)
    return amount * rate


def _lookup_rate(currency: str, on_date: date, base: str) -> float:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT rate_to_base FROM fx_rates WHERE date = ? AND currency = ?",
            (on_date.isoformat(), currency),
        ).fetchone()
        if row:
            return row["rate_to_base"]
        # Until the rate fetcher is wired up, refuse to silently misprice.
        raise LookupError(f"No FX rate for {currency} -> {base} on {on_date}")
    finally:
        conn.close()
