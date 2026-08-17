import sqlite3

DB = "borsa.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 70)
print("FINANCIAL REPORTS KONTROL")
print("=" * 70)

# ----------------------------------------------------------
# TOPLAM KAYIT
# ----------------------------------------------------------

count = cur.execute(
    "SELECT COUNT(*) FROM financial_reports"
).fetchone()[0]

print()
print("TOPLAM KAYIT:", count)

# ----------------------------------------------------------
# ASTOR KAYITLARI
# ----------------------------------------------------------

rows = cur.execute(
    """
    SELECT
        symbol,
        period,
        period_end,
        revenue,
        operating_profit,
        net_profit,
        cash,
        total_assets,
        equity,
        operating_cash_flow
    FROM financial_reports
    WHERE symbol = ?
    ORDER BY period_end
    """,
    ("ASTOR",)
).fetchall()

print()
print("ASTOR KAYITLARI")
print("-" * 70)

for row in rows:
    print(row)

# ----------------------------------------------------------
# TÜM SEMBOLLERDEN ÖRNEK
# ----------------------------------------------------------

symbols = cur.execute(
    """
    SELECT DISTINCT symbol
    FROM financial_reports
    ORDER BY symbol
    LIMIT 20
    """
).fetchall()

print()
print("İLK 20 SEMBOL")
print("-" * 70)

for row in symbols:
    print(row[0])

conn.close()

print()
print("=" * 70)
print("KONTROL TAMAMLANDI")
print("=" * 70)