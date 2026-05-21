PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    bank        TEXT NOT NULL,
    currency    TEXT NOT NULL,
    number      TEXT UNIQUE,
    account_type TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id                  INTEGER PRIMARY KEY,
    parent_id           INTEGER REFERENCES categories(id),
    name                TEXT NOT NULL,
    budget_monthly_base REAL,
    UNIQUE (parent_id, name)
);

CREATE TABLE IF NOT EXISTS rules (
    id                       INTEGER PRIMARY KEY,
    pattern                  TEXT NOT NULL,
    category_id              INTEGER NOT NULL REFERENCES categories(id),
    priority                 INTEGER NOT NULL DEFAULT 100,
    created_from_correction  INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pattern, category_id)
);

CREATE TABLE IF NOT EXISTS statements (
    id           INTEGER PRIMARY KEY,
    account_id   INTEGER REFERENCES accounts(id),  -- nullable: a statement may span several accounts
    bank         TEXT,
    period_start TEXT,
    period_end   TEXT,
    imported_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    source_file  TEXT,
    sha256       TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS fx_rates (
    date         TEXT NOT NULL,
    currency     TEXT NOT NULL,
    rate_to_base REAL NOT NULL,
    PRIMARY KEY (date, currency)
);

CREATE TABLE IF NOT EXISTS recurring_groups (
    id            INTEGER PRIMARY KEY,
    merchant      TEXT NOT NULL,
    cadence_days  INTEGER NOT NULL,
    avg_amount    REAL,
    last_seen     TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY,
    account_id          INTEGER NOT NULL REFERENCES accounts(id),
    statement_id        INTEGER REFERENCES statements(id),
    date                TEXT NOT NULL,
    amount_native       REAL NOT NULL,
    currency            TEXT NOT NULL,
    amount_base         REAL,  -- nullable until an FX rate is available for non-base currencies
    description         TEXT NOT NULL,
    merchant            TEXT,
    operation           TEXT,
    category_id         INTEGER REFERENCES categories(id),
    is_recurring        INTEGER NOT NULL DEFAULT 0,
    recurring_group_id  INTEGER REFERENCES recurring_groups(id),
    is_anomaly          INTEGER NOT NULL DEFAULT 0,
    anomaly_score       REAL,
    raw_json            TEXT,
    dedup_hash          TEXT NOT NULL UNIQUE,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_date     ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_tx_account  ON transactions(account_id);

CREATE TABLE IF NOT EXISTS corrections (
    id               INTEGER PRIMARY KEY,
    transaction_id   INTEGER NOT NULL REFERENCES transactions(id),
    old_category_id  INTEGER REFERENCES categories(id),
    new_category_id  INTEGER NOT NULL REFERENCES categories(id),
    ts               TEXT DEFAULT CURRENT_TIMESTAMP
);
