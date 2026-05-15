import sqlite3
from contextlib import contextmanager
from pathlib import Path

from expense_tracker.config import DB_PATH

SCHEMA_FILE = Path(__file__).parent / "schema.sql"
SEED_FILE = Path(__file__).parent / "seed.sql"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_FILE.read_text())
        conn.executescript(SEED_FILE.read_text())
        conn.commit()


@contextmanager
def transaction():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
