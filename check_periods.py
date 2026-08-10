import sqlite3

conn = sqlite3.connect("borsa.db")

rows = conn.execute("""
SELECT symbol, period, period_end
FROM financial_statements
ORDER BY symbol, period_end
""").fetchall()

print("=" * 70)
print("FINANCIAL STATEMENTS KAYITLARI")
print("=" * 70)

for row in rows:
    print(row)

print("=" * 70)
print("TOPLAM KAYIT:", len(rows))

conn.close()