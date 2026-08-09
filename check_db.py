import sqlite3

db = sqlite3.connect("borsa.db")

tables = db.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table'"
).fetchall()

print(tables)

db.close()
