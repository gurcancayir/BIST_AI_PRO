import sqlite3

conn = sqlite3.connect("borsa.db")

rows = conn.execute("""
SELECT
    symbol,
    fiscal_year,
    fiscal_period,
    revenue_score,
    profit_score,
    margin_score,
    debt_score,
    equity_score,
    cash_flow_score,
    growth_score,
    total_score,
    signal
FROM financial_scores
WHERE fiscal_year = 2026
  AND fiscal_period = '2026_2Q'
ORDER BY total_score DESC
""").fetchall()

print("=" * 90)
print("2026 / 2Ç FINANCIAL SCORES")
print("=" * 90)

for row in rows:
    print(row)

print("=" * 90)
print("TOPLAM KAYIT:", len(rows))

conn.close()