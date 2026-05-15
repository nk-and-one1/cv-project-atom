import hashlib
import json
from abc import ABC, abstractmethod
from datetime import date
from typing import IO, Iterable

from pydantic import BaseModel, Field


class RawTransaction(BaseModel):
    """Parser output before currency conversion and categorization."""

    date: date
    amount_native: float
    currency: str
    description: str
    merchant: str | None = None
    raw: dict = Field(default_factory=dict)

    def dedup_hash(self, account_id: int) -> str:
        payload = f"{account_id}|{self.date.isoformat()}|{self.amount_native:.2f}|{self.description}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def raw_json(self) -> str:
        return json.dumps(self.raw, default=str, sort_keys=True)


class StatementParser(ABC):
    """One implementation per bank + format (CSV/PDF)."""

    bank: str
    format: str

    @abstractmethod
    def parse(self, source: IO[bytes]) -> Iterable[RawTransaction]:
        ...
