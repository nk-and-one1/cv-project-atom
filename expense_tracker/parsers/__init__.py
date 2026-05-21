"""Parser registry. Add a bank by registering its parser class here."""

from expense_tracker.parsers.base import StatementParser

KNOWN_BANKS = ("freedom",)


def get_parser(bank: str) -> StatementParser:
    if bank == "freedom":
        from expense_tracker.parsers.pdf.freedom import FreedomBankPDFParser

        return FreedomBankPDFParser()
    raise ValueError(f"No parser for bank {bank!r}. Known: {KNOWN_BANKS}")
