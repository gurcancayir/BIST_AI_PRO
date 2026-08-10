import sqlite3

c = sqlite3.connect("borsa.db")

row = c.execute("""
SELECT
    revenue,
    net_profit,
    cash,
    equity,
    operating_cash_flow
FROM financial_statements
WHERE symbol = 'THYAO'
AND period = '2026_2Q'
""").fetchone()

print(row)

c.close()
