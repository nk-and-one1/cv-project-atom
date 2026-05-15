"""Stub for the first bank parser.

Fill this in once we have a sample statement. The body should:
  1. Read the CSV via csv.DictReader or pandas.
  2. Yield one RawTransaction per row using the bank's column mapping.
  3. Handle date format, decimal separator, and signed amounts (debit/credit).
"""

from typing import IO, Iterable

from expense_tracker.parsers.base import RawTransaction, StatementParser


class KaspiCSVParser(StatementParser):
    bank = "kaspi"
    format = "csv"

    def parse(self, source: IO[bytes]) -> Iterable[RawTransaction]:
        raise NotImplementedError("Provide a sample statement to wire this up.")
