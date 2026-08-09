import sqlite3

db = sqlite3.connect("borsa.db")

rows = db.execute("""
SELECT
    symbol,
    fiscal_year,
    fiscal_period,
    total_score,
    signal
FROM financial_scores
ORDER BY
    symbol,
    fiscal_year DESC,
    fiscal_period DESC
""").fetchall()

for row in rows:
    print(row)

db.close()
