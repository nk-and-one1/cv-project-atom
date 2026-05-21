"""Parser for AO "Freedom Bank Kazakhstan" card statements (PDF, Russian).

Layout (verified against a real statement):
  - Page 0: account-summary table (Номер счёта | Валюта | Остаток) and an
    operation-summary table (operation type -> signed total in KZT).
  - Pages 1+: transaction table  Дата | Сумма | Валюта | Операция | Детали
    Borderless; pdfplumber recovers cells by alignment and keeps wrapped
    "Детали" cells together with a newline.

A statement can cover several accounts (e.g. one USD + one KZT). Each row carries
its own currency, so the pipeline maps a row to the account with that currency.
"""

import re
from datetime import date, datetime
from typing import IO

from expense_tracker.parsers.base import (
    OperationSummary,
    ParsedStatement,
    RawTransaction,
    StatementAccount,
    StatementParser,
)
from expense_tracker.parsers.pdf.extract import read_pdf

HEADER = ["Дата", "Сумма", "Валюта", "Операция", "Детали"]
SYMBOL_TO_CCY = {"₸": "KZT", "$": "USD", "€": "EUR", "₽": "RUB"}
OPERATION_TYPES = {
    "Платеж", "Перевод", "Покупка", "Снятие", "Платеж по кредиту",
    "Пополнение", "Сумма в обработке", "Погашение", "Овердрафт", "Другое",
}

_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_PERIOD_RE = re.compile(r"за период с (\d{2}\.\d{2}\.\d{4}) по (\d{2}\.\d{2}\.\d{4})")
_ACCOUNT_RE = re.compile(r"(KZ[0-9A-Z]{18})\s+(KZT|USD|EUR|RUB)\s+([\d\s,]+\.\d{2})")


def _to_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%d.%m.%Y").date()


def _to_number(s: str) -> float:
    return float(re.sub(r"[,\s]", "", s.strip()))


def _amount_and_ccy(cell: str) -> tuple[float, str | None]:
    text = (cell or "").strip()
    ccy = None
    for sym, code in SYMBOL_TO_CCY.items():
        if sym in text:
            ccy = code
            text = text.replace(sym, "")
    return _to_number(text), ccy


def _clean(detail: str | None) -> str:
    return re.sub(r"\s+", " ", (detail or "").replace("\n", " ")).strip()


class FreedomBankPDFParser(StatementParser):
    bank = "freedom"
    format = "pdf"

    def parse(self, source: IO[bytes]) -> ParsedStatement:
        pages = read_pdf(source)
        full_text = "\n".join(p.text for p in pages)

        period_start, period_end = self._period(full_text)
        accounts = self._accounts(full_text)
        summary = self._summary(pages)
        transactions = self._transactions(pages)

        return ParsedStatement(
            bank=self.bank,
            period_start=period_start,
            period_end=period_end,
            accounts=accounts,
            summary=summary,
            transactions=transactions,
        )

    @staticmethod
    def _period(text: str) -> tuple[date | None, date | None]:
        m = _PERIOD_RE.search(text)
        return (_to_date(m.group(1)), _to_date(m.group(2))) if m else (None, None)

    @staticmethod
    def _accounts(text: str) -> list[StatementAccount]:
        return [
            StatementAccount(number=m.group(1), currency=m.group(2), balance=_to_number(m.group(3)))
            for m in _ACCOUNT_RE.finditer(text)
        ]

    @staticmethod
    def _summary(pages) -> list[OperationSummary]:
        out: list[OperationSummary] = []
        for page in pages:
            for table in page.tables:
                for row in table:
                    if len(row) >= 2 and row[0] in OPERATION_TYPES and row[1]:
                        total, ccy = _amount_and_ccy(row[1])
                        out.append(OperationSummary(operation=row[0], currency=ccy or "KZT", total=total))
        return out

    @staticmethod
    def _transactions(pages) -> list[RawTransaction]:
        txns: list[RawTransaction] = []
        per_date_seq: dict[date, int] = {}
        for page in pages:
            for table in page.tables:
                if not table or [c.strip() if c else c for c in table[0][:5]] != HEADER:
                    continue
                for row in table[1:]:
                    if len(row) < 5 or not row[0] or not _DATE_RE.match(row[0].strip()):
                        continue
                    d = _to_date(row[0])
                    amount, _sym_ccy = _amount_and_ccy(row[1])
                    currency = (row[2] or "").strip()
                    operation = (row[3] or "").strip()
                    description = _clean(row[4])
                    seq = per_date_seq.get(d, 0)
                    per_date_seq[d] = seq + 1
                    txns.append(RawTransaction(
                        date=d,
                        amount_native=amount,
                        currency=currency,
                        description=description,
                        operation=operation,
                        seq=seq,
                        raw={"row": [c for c in row[:5]]},
                    ))
        return txns
