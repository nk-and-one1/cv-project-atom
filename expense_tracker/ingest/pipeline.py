"""Ingest pipeline: parse -> map accounts -> dedup -> convert -> categorize -> store."""

import hashlib
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import IO

from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import transaction
from expense_tracker.fx.rates import convert_to_base
from expense_tracker.parsers.base import ParsedStatement, RawTransaction, StatementParser


@dataclass
class IngestResult:
    inserted: int = 0
    duplicates: int = 0
    uncategorized: int = 0
    needs_fx: int = 0
    accounts: int = 0
    warnings: list[str] = field(default_factory=list)


def file_sha256(source: IO[bytes]) -> str:
    h = hashlib.sha256()
    source.seek(0)
    for chunk in iter(lambda: source.read(8192), b""):
        h.update(chunk)
    source.seek(0)
    return h.hexdigest()


def reconcile(parsed: ParsedStatement) -> list[str]:
    """Compare parsed per-(operation, currency) totals against the bank's printed summary."""
    got: dict[tuple[str | None, str], float] = defaultdict(float)
    for tx in parsed.transactions:
        got[(tx.operation, tx.currency)] += tx.amount_native

    warnings: list[str] = []
    for s in parsed.summary:
        actual = got.get((s.operation, s.currency), 0.0)
        delta = actual - s.total
        if abs(delta) > 0.01:
            warnings.append(
                f"{s.operation}/{s.currency}: parsed {actual:,.2f} vs summary {s.total:,.2f} (Δ {delta:,.2f})"
            )
    return warnings


def _upsert_account(conn: sqlite3.Connection, bank: str, number: str, currency: str) -> int:
    row = conn.execute("SELECT id FROM accounts WHERE number = ?", (number,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO accounts (name, bank, currency, number) VALUES (?, ?, ?, ?)",
        (f"{bank} {currency}", bank, currency, number),
    )
    return cur.lastrowid


def ingest(source: IO[bytes], parser: StatementParser, filename: str) -> IngestResult:
    """End-to-end ingest for one statement file.

    Skips on duplicate file hash; skips per-row on duplicate dedup_hash. Each row is
    mapped to the account matching its currency. Non-base currencies without a cached
    FX rate are stored with amount_base = NULL and counted in `needs_fx`.
    """
    from expense_tracker.categorize.rules import categorize_with_rules  # avoid import cycle

    parsed = parser.parse(source)
    sha = file_sha256(source)
    result = IngestResult(warnings=reconcile(parsed))

    with transaction() as conn:
        if conn.execute("SELECT 1 FROM statements WHERE sha256 = ?", (sha,)).fetchone():
            result.warnings.append("This file was already imported (matching checksum).")
            return result

        # Resolve accounts declared on the statement, keyed by currency.
        ccy_to_account: dict[str, int] = {}
        for acct in parsed.accounts:
            ccy_to_account[acct.currency] = _upsert_account(conn, parsed.bank, acct.number, acct.currency)
        result.accounts = len(ccy_to_account)

        primary_account = next(iter(ccy_to_account.values()), None)
        cur = conn.execute(
            "INSERT INTO statements (account_id, bank, period_start, period_end, source_file, sha256) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                primary_account, parsed.bank,
                parsed.period_start.isoformat() if parsed.period_start else None,
                parsed.period_end.isoformat() if parsed.period_end else None,
                filename, sha,
            ),
        )
        statement_id = cur.lastrowid

        for raw_tx in parsed.transactions:
            account_id = _resolve_account(conn, ccy_to_account, parsed.bank, raw_tx)
            dedup = raw_tx.dedup_hash(account_id)
            if conn.execute("SELECT 1 FROM transactions WHERE dedup_hash = ?", (dedup,)).fetchone():
                result.duplicates += 1
                continue

            try:
                amount_base = convert_to_base(
                    amount=raw_tx.amount_native, currency=raw_tx.currency,
                    on_date=raw_tx.date, base=BASE_CURRENCY,
                )
            except LookupError:
                amount_base = None
                result.needs_fx += 1

            category_id = categorize_with_rules(conn, raw_tx.description, raw_tx.merchant)
            if category_id is None:
                result.uncategorized += 1

            conn.execute(
                """
                INSERT INTO transactions (
                    account_id, statement_id, date, amount_native, currency, amount_base,
                    description, merchant, operation, category_id, raw_json, dedup_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, statement_id, raw_tx.date.isoformat(),
                    raw_tx.amount_native, raw_tx.currency, amount_base,
                    raw_tx.description, raw_tx.merchant, raw_tx.operation, category_id,
                    raw_tx.raw_json(), dedup,
                ),
            )
            result.inserted += 1

    return result


def _resolve_account(
    conn: sqlite3.Connection, ccy_to_account: dict[str, int], bank: str, raw_tx: RawTransaction
) -> int:
    account_id = ccy_to_account.get(raw_tx.currency)
    if account_id is None:
        # Statement listed no account for this currency; synthesize a stable one.
        account_id = _upsert_account(conn, bank, f"{bank}-{raw_tx.currency}", raw_tx.currency)
        ccy_to_account[raw_tx.currency] = account_id
    return account_id
