"""Ingest pipeline: parse -> dedup -> convert -> categorize -> store."""

import hashlib
from dataclasses import dataclass
from typing import IO

from expense_tracker.config import BASE_CURRENCY
from expense_tracker.db.connection import transaction
from expense_tracker.fx.rates import convert_to_base
from expense_tracker.parsers.base import StatementParser


@dataclass
class IngestResult:
    inserted: int
    duplicates: int
    uncategorized: int


def file_sha256(source: IO[bytes]) -> str:
    h = hashlib.sha256()
    source.seek(0)
    for chunk in iter(lambda: source.read(8192), b""):
        h.update(chunk)
    source.seek(0)
    return h.hexdigest()


def ingest(source: IO[bytes], parser: StatementParser, account_id: int, filename: str) -> IngestResult:
    """End-to-end ingest for one statement file.

    Skips on duplicate file hash; skips per-row on duplicate dedup_hash.
    Categorization is delegated to expense_tracker.categorize.rules + llm.
    """
    from expense_tracker.categorize.rules import categorize_with_rules  # local import to avoid cycles

    sha = file_sha256(source)
    inserted = duplicates = uncategorized = 0

    with transaction() as conn:
        cur = conn.execute("SELECT id FROM statements WHERE sha256 = ?", (sha,))
        if cur.fetchone():
            return IngestResult(0, 0, 0)

        cur = conn.execute(
            "INSERT INTO statements (account_id, source_file, sha256) VALUES (?, ?, ?)",
            (account_id, filename, sha),
        )
        statement_id = cur.lastrowid

        for raw_tx in parser.parse(source):
            dedup = raw_tx.dedup_hash(account_id)
            existing = conn.execute(
                "SELECT 1 FROM transactions WHERE dedup_hash = ?", (dedup,)
            ).fetchone()
            if existing:
                duplicates += 1
                continue

            amount_base = convert_to_base(
                amount=raw_tx.amount_native,
                currency=raw_tx.currency,
                on_date=raw_tx.date,
                base=BASE_CURRENCY,
            )

            category_id = categorize_with_rules(conn, raw_tx.description, raw_tx.merchant)
            if category_id is None:
                uncategorized += 1

            conn.execute(
                """
                INSERT INTO transactions (
                    account_id, statement_id, date,
                    amount_native, currency, amount_base,
                    description, merchant, category_id,
                    raw_json, dedup_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, statement_id, raw_tx.date.isoformat(),
                    raw_tx.amount_native, raw_tx.currency, amount_base,
                    raw_tx.description, raw_tx.merchant, category_id,
                    raw_tx.raw_json(), dedup,
                ),
            )
            inserted += 1

    return IngestResult(inserted, duplicates, uncategorized)
