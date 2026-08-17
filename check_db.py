import sqlite3

DB_PATH = "borsa.db"

conn = sqlite3.connect(DB_PATH)

conn.execute("""
CREATE TABLE IF NOT EXISTS financial_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    period_end TEXT NOT NULL,
    report_type TEXT,
    currency TEXT DEFAULT 'TRY',

    revenue REAL,
    cost_of_sales REAL,
    operating_profit REAL,
    depreciation_amortization REAL,
    ebitda REAL,
    net_profit REAL,
    interest_expense REAL,

    cash REAL,
    short_term_financial_debt REAL,
    current_portion_long_term_debt REAL,
    long_term_financial_debt REAL,

    trade_receivables REAL,
    inventory REAL,

    current_assets REAL,
    current_liabilities REAL,

    total_assets REAL,
    equity REAL,

    operating_cash_flow REAL,

    source TEXT DEFAULT 'KAP',
    source_date TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

print("financial_reports tablosu hazır.")

tables = conn.execute(
    "SELECT name FROM sqlite_master "
    "WHERE type='table' ORDER BY name"
).fetchall()

print("\n=== TABLOLAR ===")

for table in tables:
    print(table[0])

conn.close()