import sqlite3

db = sqlite3.connect("borsa.db")

print("\n=== ASTOR FINANCIAL STATEMENTS ===")

rows = db.execute("""
SELECT
    symbol,
    period,
    period_end,
    report_type,
    revenue,
    operating_profit,
    ebitda,
    net_profit,
    cash,
    current_assets,
    current_liabilities,
    total_assets,
    equity,
    operating_cash_flow,
    source
FROM financial_statements
WHERE symbol = 'ASTOR'
ORDER BY period_end DESC
""").fetchall()

for row in rows:
    print(row)

print("\n=== ASTOR FINANCIAL SCORES ===")

rows = db.execute("""
SELECT
    symbol,
    fiscal_year,
    fiscal_period,
    revenue_score,
    profit_score,
    margin_score,
    debt_score,
    equity_score,
    cash_flow_score,
    growth_score,
    total_score,
    signal
FROM financial_scores
WHERE symbol = 'ASTOR'
ORDER BY fiscal_year DESC
""").fetchall()

for row in rows:
    print(row)

db.close()
