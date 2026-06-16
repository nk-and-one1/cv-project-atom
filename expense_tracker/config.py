import os
from pathlib import Path

BASE_CURRENCY = os.environ.get("EXPENSE_TRACKER_BASE_CURRENCY", "KZT")

DATA_DIR = Path(os.environ.get("EXPENSE_TRACKER_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "expenses.sqlite"

DATA_DIR.mkdir(parents=True, exist_ok=True)
