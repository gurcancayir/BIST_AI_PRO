import sqlite3
import pandas as pd

c = sqlite3.connect("borsa.db")

df = pd.read_sql_query("""
SELECT
    symbol,
    period,
    period_end,
    revenue,
    net_profit,
    cash,
    equity,
    operating_cash_flow,
    short_term_financial_debt,
    current_portion_long_term_debt,
    long_term_financial_debt
FROM financial_statements
WHERE period = '2026_2Q'
ORDER BY symbol
""", c)

c.close()

print(df.to_string(index=False))
