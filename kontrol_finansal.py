from database.database import get_connection

conn = get_connection()

rows = conn.execute("""
SELECT
    symbol,
    period,
    period_end,
    revenue,
    operating_profit,
    net_profit,
    operating_cash_flow,
    depreciation_amortization
FROM financial_statements
WHERE symbol = 'ASTOR'
ORDER BY period_end DESC
""").fetchall()

conn.close()

print("\n=== ASTOR FİNANSAL VERİLER ===")

if not rows:
    print("ASTOR için kayıt bulunamadı.")
else:
    for row in rows:
        print(dict(row))