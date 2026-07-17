import sqlite3


conn = sqlite3.connect("data/portfolio.db")
row = conn.execute(
    """
    SELECT id, date, symbol, type, quantity, price, commission
    FROM transactions
    WHERE symbol = ?
      AND date = ?
      AND type = ?
      AND quantity = ?
      AND ABS(price - ?) < 0.0001
    """,
    ("CVKMD", "2026-01-27", "sell", 200, 35.20),
).fetchall()

print(row)

if len(row) != 1:
    raise SystemExit(f"Beklenen tek satir bulunamadi. Eslesen satir sayisi: {len(row)}")

transaction_id = row[0][0]
conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
conn.commit()
print(f"Silindi: id={transaction_id}")
