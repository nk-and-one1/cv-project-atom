import os
from pathlib import Path

BASE_CURRENCY = os.environ.get("EXPENSE_TRACKER_BASE_CURRENCY", "KZT")

DATA_DIR = Path(os.environ.get("EXPENSE_TRACKER_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "expenses.sqlite"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LLM_MODEL = os.environ.get("EXPENSE_TRACKER_LLM_MODEL", "claude-haiku-4-5-20251001")

DATA_DIR.mkdir(parents=True, exist_ok=True)
