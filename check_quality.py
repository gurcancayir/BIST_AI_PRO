import sqlite3

db = sqlite3.connect("borsa.db")

rows = db.execute("""
SELECT
    symbol,
    period,
    period_end,
    net_margin,
    net_debt_ebitda,
    cfo,
    current_ratio,
    equity_asset_ratio,
    interest_coverage,
    receivable_days,
    inventory_days,
    net_debt_equity,
    revenue_growth,
    data_quality
FROM balance_sheet_quality
ORDER BY period_end DESC
""").fetchall()

for row in rows:
    print(row)

db.close()
