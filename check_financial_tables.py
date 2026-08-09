import sqlite3

db = sqlite3.connect("borsa.db")

for table in ["financial_statements", "balance_sheet_quality", "financial_scores"]:
    print("\n==============================")
    print(table)
    print("==============================")

    rows = db.execute(f"PRAGMA table_info({table})").fetchall()

    for row in rows:
        print(row)

db.close()
