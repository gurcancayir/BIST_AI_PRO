import sqlite3

db = sqlite3.connect("borsa.db")

rows = db.execute("SELECT * FROM balance_sheet_quality").fetchall()

print("KAYIT SAYISI:", len(rows))

for row in rows:
    print(repr(row))

db.close()
