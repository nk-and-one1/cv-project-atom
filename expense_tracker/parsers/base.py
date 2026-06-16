import hashlib
import json
from abc import ABC, abstractmethod
from datetime import date
from typing import IO

from pydantic import BaseModel, Field


class RawTransaction(BaseModel):
    """Parser output before currency conversion and categorization."""

    date: date
    amount_native: float
    currency: str
    description: str
    merchant: str | None = None
    operation: str | None = None  # bank's own operation label, e.g. "Покупка"
    seq: int = 0  # ordinal within its (statement, date) — keeps legit same-day dupes distinct
    raw: dict = Field(default_factory=dict)

    def dedup_hash(self, account_id: int) -> str:
        payload = (
            f"{account_id}|{self.date.isoformat()}|{self.amount_native:.2f}"
            f"|{self.description}|{self.seq}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def raw_json(self) -> str:
        return json.dumps(self.raw, default=str, sort_keys=True)


class StatementAccount(BaseModel):
    number: str
    currency: str
    balance: float | None = None


class OperationSummary(BaseModel):
    """A per-operation-type total the bank prints on the statement, for reconciliation."""

    operation: str
    currency: str
    total: float


class ParsedStatement(BaseModel):
    bank: str
    period_start: date | None = None
    period_end: date | None = None
    accounts: list[StatementAccount] = Field(default_factory=list)
    summary: list[OperationSummary] = Field(default_factory=list)
    transactions: list[RawTransaction] = Field(default_factory=list)


class StatementParser(ABC):
    """One implementation per bank + format."""

    bank: str
    format: str

    @abstractmethod
    def parse(self, source: IO[bytes]) -> ParsedStatement:
        ...
