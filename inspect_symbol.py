import sqlite3
import sys

import pandas as pd


symbols = [symbol.upper() for symbol in sys.argv[1:]]
if not symbols:
    raise SystemExit("Kullanim: python inspect_symbol.py ASTOR CVKMD")

placeholders = ",".join(["?"] * len(symbols))
conn = sqlite3.connect("data/portfolio.db")

df = pd.read_sql_query(
    f"""
    SELECT id, date, symbol, type, quantity, price, commission
    FROM transactions
    WHERE symbol IN ({placeholders})
    ORDER BY symbol, date, id
    """,
    conn,
    params=symbols,
)

if df.empty:
    print("Kayit bulunamadi.")
    raise SystemExit

print(df.to_string(index=False))
print()
print("OZET")
print(df.groupby(["symbol", "type"])["quantity"].sum().to_string())
print()
net = (
    df.assign(
        signed_quantity=df.apply(
            lambda row: row["quantity"] if row["type"] == "buy" else -row["quantity"],
            axis=1,
        )
    )
    .groupby("symbol")["signed_quantity"]
    .sum()
)
print("NET ADET")
print(net.to_string())

print()
print("ELDEKI ADET ASIMI KONTROLU")
for symbol, symbol_df in df.groupby("symbol"):
    holding = 0.0
    warnings = []
    for row in symbol_df.sort_values(["date", "id"]).itertuples():
        if row.type == "buy":
            holding += float(row.quantity)
        elif row.type == "sell":
            quantity = float(row.quantity)
            if quantity > holding:
                warnings.append(
                    f"{row.date} id={row.id}: {quantity:g} satis var, onceki eldeki adet {holding:g}"
                )
                holding = 0.0
            else:
                holding -= quantity
    print(symbol)
    if warnings:
        print("\n".join(warnings))
    else:
        print("Asim yok.")
