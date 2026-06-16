# Expense Tracker

Personal finance app: ingest bank statements (CSV/PDF), categorize transactions
with rules + LLM fallback, and explore them in a pivot table.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run expense_tracker/ui/streamlit_app.py
```

The SQLite DB and any imported statements live under `./data/` (gitignored).

## Configuration

| Env var                          | Default                       | Notes                  |
| -------------------------------- | ----------------------------- | ---------------------- |
| `EXPENSE_TRACKER_BASE_CURRENCY`  | `KZT`                         | Reporting currency     |
| `EXPENSE_TRACKER_DATA_DIR`       | `data`                        | DB + statements        |
| `ANTHROPIC_API_KEY`              | -                             | For LLM categorizer    |
| `EXPENSE_TRACKER_LLM_MODEL`      | `claude-haiku-4-5-20251001`   | Cheap + fast fallback  |

## Status

Skeleton only. Next:
1. Wire `parsers/csv/kaspi.py` against a real statement.
2. Wire `categorize/llm.py` to the Anthropic SDK.
3. Wire `fx/rates.py` to a rates source (exchangerate.host or NBK).

See `expense_tracker/` for the module layout.
