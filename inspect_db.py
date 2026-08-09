import sqlite3
import os

print("CALISAN KLASOR:")
print(os.getcwd())

print("\nDB DOSYASI:")
print(os.path.abspath("borsa.db"))

db = sqlite3.connect("borsa.db")

for table in ["financial_statements", "balance_sheet_quality", "financial_scores"]:
    print("\n", table)

    count = db.execute(
        "SELECT COUNT(*) FROM " + table
    ).fetchone()[0]

    print("COUNT =", count)

    rows = db.execute(
        "SELECT * FROM " + table + " LIMIT 5"
    ).fetchall()

    print("ROWS =", rows)

db.close()
