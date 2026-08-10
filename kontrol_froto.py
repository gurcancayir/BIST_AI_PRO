import sqlite3

db = sqlite3.connect("borsa.db")

# ==========================================================
# THYAO
# Mevcut değerler 1000 kat küçük.
# ==========================================================

db.execute("""
UPDATE financial_statements
SET
    revenue = revenue * 1000,
    net_profit = net_profit * 1000,
    cash = cash * 1000,
    total_assets = total_assets * 1000,
    equity = equity * 1000,
    operating_cash_flow = operating_cash_flow * 1000,
    short_term_financial_debt =
        short_term_financial_debt * 1000,
    current_portion_long_term_debt =
        current_portion_long_term_debt * 1000,
    long_term_financial_debt =
        long_term_financial_debt * 1000
WHERE symbol = 'THYAO'
""")

# ==========================================================
# ASTOR
# Mevcut değerler 1000 kat büyük.
# ==========================================================

db.execute("""
UPDATE financial_statements
SET
    revenue = revenue / 1000,
    net_profit = net_profit / 1000,
    cash = cash / 1000,
    total_assets = total_assets / 1000,
    equity = equity / 1000,
    operating_cash_flow =
        operating_cash_flow / 1000,
    short_term_financial_debt =
        short_term_financial_debt / 1000,
    current_portion_long_term_debt =
        current_portion_long_term_debt / 1000,
    long_term_financial_debt =
        long_term_financial_debt / 1000
WHERE symbol = 'ASTOR'
""")

db.commit()

print("THYAO düzeltildi: x1000")
print("ASTOR düzeltildi: /1000")

db.close()