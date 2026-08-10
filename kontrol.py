import sqlite3

conn = sqlite3.connect("borsa.db")

rows = conn.execute("""
SELECT
    symbol,
    period,
    revenue,
    net_profit,
    equity
FROM financial_statements
WHERE period = '2026_2Q'
ORDER BY symbol
""").fetchall()

for row in rows:
    print(row)

conn.close()