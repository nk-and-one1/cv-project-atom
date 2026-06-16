"""Import-tab formatters: must tolerate missing balances and periods."""

from datetime import date

from expense_tracker.parsers.base import ParsedStatement, RawTransaction, StatementAccount
from expense_tracker.ui.tabs.import_tab import _format_accounts, _format_summary


def test_format_accounts_handles_missing_balance():
    accounts = [
        StatementAccount(number="KZ123456789012345678", currency="KZT", balance=1234.5),
        StatementAccount(number="KZ000000000000000099", currency="USD", balance=None),
    ]
    # The None balance must render without a balance segment and without raising.
    assert _format_accounts(accounts) == "KZT …345678 (balance 1,234.50) · USD …000099"


def test_format_accounts_empty():
    assert _format_accounts([]) == ""


def test_format_summary_with_period():
    parsed = ParsedStatement(
        bank="freedom",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        accounts=[StatementAccount(number="KZ1", currency="KZT")],
        transactions=[RawTransaction(date=date(2024, 1, 5), amount_native=-1.0, currency="KZT", description="x")],
    )
    summary = _format_summary(parsed)
    assert "Parsed 1 transactions" in summary
    assert "1 account(s)" in summary
    assert "2024-01-01 → 2024-01-31" in summary


def test_format_summary_without_period():
    summary = _format_summary(ParsedStatement(bank="freedom", transactions=[]))
    assert "Parsed 0 transactions" in summary
    assert "period unknown" in summary
