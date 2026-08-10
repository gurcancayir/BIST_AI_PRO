import sqlite3

conn = sqlite3.connect("borsa.db")

rows = conn.execute("""
SELECT
    symbol,
    period,
    revenue,
    net_profit,
    cash,
    total_assets,
    equity,
    operating_cash_flow,
    short_term_financial_debt,
    current_portion_long_term_debt,
    long_term_financial_debt
FROM financial_statements
WHERE period = '2026_2Q'
ORDER BY symbol
""").fetchall()

print("=" * 100)
print("2026 / 2Ç FINANSAL VERİLER")
print("=" * 100)

for row in rows:
    print()
    print("HİSSE:", row[0])
    print("Dönem:", row[1])
    print("Hasılat:", row[2])
    print("Net kâr:", row[3])
    print("Nakit:", row[4])
    print("Toplam varlık:", row[5])
    print("Özkaynak:", row[6])
    print("Faaliyet nakit akışı:", row[7])
    print("Kısa vadeli borç:", row[8])
    print("KV uzun vadeli borç:", row[9])
    print("Uzun vadeli borç:", row[10])

print()
print("=" * 100)
print("TOPLAM 2026/2Ç KAYDI:", len(rows))
print("=" * 100)

conn.close()