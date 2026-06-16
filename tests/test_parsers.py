"""Freedom Bank PDF parsing helpers, reconciliation, and dedup hashing.

These exercise the pure parsing logic by feeding fake page/table structures,
so no real PDF is required.
"""

from datetime import date

from expense_tracker.ingest.pipeline import reconcile
from expense_tracker.parsers.base import OperationSummary, ParsedStatement, RawTransaction
from expense_tracker.parsers.pdf.freedom import (
    FreedomBankPDFParser,
    _amount_and_ccy,
    _clean,
    _to_date,
    _to_number,
)


class FakePage:
    def __init__(self, text="", tables=None):
        self.text = text
        self.tables = tables or []


def test_to_date():
    assert _to_date("31.12.2024") == date(2024, 12, 31)
    assert _to_date("  01.02.2023 ") == date(2023, 2, 1)


def test_to_number_strips_spaces_and_thousands_separators():
    assert _to_number("1 234.56") == 1234.56
    assert _to_number("1,234.56") == 1234.56
    assert _to_number("-2 000.00") == -2000.0
    assert _to_number("750.00") == 750.0


def test_amount_and_ccy_detects_symbol():
    assert _amount_and_ccy("1 234.56 ₸") == (1234.56, "KZT")
    assert _amount_and_ccy("$100.00") == (100.0, "USD")
    assert _amount_and_ccy("50.00") == (50.0, None)


def test_clean_collapses_whitespace():
    assert _clean("foo\n  bar   baz ") == "foo bar baz"
    assert _clean(None) == ""


def test_period_extraction():
    text = "Выписка за период с 01.01.2024 по 31.01.2024 ..."
    assert FreedomBankPDFParser._period(text) == (date(2024, 1, 1), date(2024, 1, 31))


def test_period_missing_returns_none():
    assert FreedomBankPDFParser._period("no period here") == (None, None)


def test_accounts_extraction():
    text = "KZ123456789012345678 KZT 1 234 567.89"
    accounts = FreedomBankPDFParser._accounts(text)
    assert len(accounts) == 1
    assert accounts[0].number == "KZ123456789012345678"
    assert accounts[0].currency == "KZT"
    assert accounts[0].balance == 1234567.89


def test_transactions_parsed_from_tables():
    header = ["Дата", "Сумма", "Валюта", "Операция", "Детали"]
    table = [
        header,
        ["10.01.2024", "1 234.56 ₸", "KZT", "Покупка", "MAGNUM ALMATY"],
        ["10.01.2024", "5 000.00 ₸", "KZT", "Покупка", "WRAPPED\nDETAIL"],
        ["bogus", "x", "", "", ""],  # not a date -> skipped
    ]
    txns = FreedomBankPDFParser._transactions([FakePage(tables=[table])])
    assert len(txns) == 2
    assert txns[0].date == date(2024, 1, 10)
    assert txns[0].amount_native == 1234.56
    assert txns[0].currency == "KZT"
    assert txns[0].operation == "Покупка"
    assert txns[0].description == "MAGNUM ALMATY"
    assert txns[1].description == "WRAPPED DETAIL"  # newline collapsed
    assert (txns[0].seq, txns[1].seq) == (0, 1)  # same-day rows stay distinct


def test_dedup_hash_is_deterministic_and_sensitive():
    base = dict(date=date(2024, 1, 1), amount_native=-100.0, currency="KZT", description="COFFEE")
    tx = RawTransaction(seq=0, **base)
    same = RawTransaction(seq=0, **base)
    other_seq = RawTransaction(seq=1, **base)
    assert tx.dedup_hash(1) == same.dedup_hash(1)
    assert tx.dedup_hash(1) != other_seq.dedup_hash(1)  # seq distinguishes same-day dupes
    assert tx.dedup_hash(1) != tx.dedup_hash(2)         # account distinguishes


def test_reconcile_flags_only_mismatches():
    parsed = ParsedStatement(
        bank="freedom",
        summary=[
            OperationSummary(operation="Покупка", currency="KZT", total=-1500.0),
            OperationSummary(operation="Перевод", currency="KZT", total=-999.0),
        ],
        transactions=[
            RawTransaction(date=date(2024, 1, 1), amount_native=-1000.0, currency="KZT", description="a", operation="Покупка"),
            RawTransaction(date=date(2024, 1, 2), amount_native=-500.0, currency="KZT", description="b", operation="Покупка"),
            RawTransaction(date=date(2024, 1, 3), amount_native=-1.0, currency="KZT", description="c", operation="Перевод"),
        ],
    )
    warnings = reconcile(parsed)
    assert len(warnings) == 1  # Покупка reconciles; Перевод does not
    assert "Перевод" in warnings[0]
