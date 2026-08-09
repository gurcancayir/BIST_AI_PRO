import sqlite3
from datetime import datetime
from pathlib import Path


# ==========================================================
# DB YOLU
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "borsa.db"


# ==========================================================
# PUAN SINIRLAMA
# ==========================================================

def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(float(value), maximum))


# ==========================================================
# GÜVENLİ BÖLME
# ==========================================================

def safe_div(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None

    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


# ==========================================================
# TEK DÖNEM FİNANSAL VERİ GETİR
# ==========================================================

def get_financial_statement(symbol, period_end=None):
    symbol = str(symbol).upper().strip()

    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if period_end:
        row = conn.execute(
            """
            SELECT *
            FROM financial_statements
            WHERE symbol = ?
              AND period_end = ?
            ORDER BY
                CASE
                    WHEN report_type = 'Konsolide' THEN 0
                    ELSE 1
                END
            LIMIT 1
            """,
            (symbol, str(period_end)),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT *
            FROM financial_statements
            WHERE symbol = ?
            ORDER BY period_end DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

    conn.close()

    return dict(row) if row else None


# ==========================================================
# ÖNCEKİ DÖNEMİ BUL
# ==========================================================

def get_previous_statement(symbol, current_period_end):
    symbol = str(symbol).upper().strip()

    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    current_date = str(current_period_end)

    try:
        year = int(current_date[:4])
        month_day = current_date[4:]
        previous_date = str(year - 1) + month_day
    except (ValueError, TypeError):
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT *
        FROM financial_statements
        WHERE symbol = ?
          AND period_end = ?
        ORDER BY
            CASE
                WHEN report_type = 'Konsolide' THEN 0
                ELSE 1
            END
        LIMIT 1
        """,
        (symbol, previous_date),
    ).fetchone()

    conn.close()

    return dict(row) if row else None
# ==========================================================
# 1 - CİRO SKORU
# AĞIRLIK: %15
# ==========================================================

def calculate_revenue_score(current, previous=None):

    revenue = current.get("revenue")

    if revenue is None or revenue <= 0:
        return 0

    if not previous:
        return 50

    previous_revenue = previous.get("revenue")

    if previous_revenue in (None, 0):
        return 50

    growth = (revenue - previous_revenue) / abs(previous_revenue)

    if growth >= 0.30:
        return 100
    elif growth >= 0.20:
        return 90
    elif growth >= 0.10:
        return 80
    elif growth >= 0.05:
        return 70
    elif growth >= 0:
        return 60
    elif growth >= -0.05:
        return 50
    elif growth >= -0.15:
        return 35
    else:
        return 20


# ==========================================================
# 2 - NET KÂR SKORU
# AĞIRLIK: %20
# ==========================================================

def calculate_profit_score(current):

    profit = current.get("net_profit")

    if profit is None:
        return 50

    if profit > 0:
        return 100
    elif profit == 0:
        return 50
    else:
        return 10


# ==========================================================
# 3 - KÂR MARJI SKORU
# AĞIRLIK: %15
# ==========================================================

def calculate_margin_score(current):

    revenue = current.get("revenue")
    profit = current.get("net_profit")

    margin = safe_div(profit, revenue)

    if margin is None:
        return 50

    if margin >= 0.20:
        return 100
    elif margin >= 0.15:
        return 90
    elif margin >= 0.10:
        return 80
    elif margin >= 0.05:
        return 70
    elif margin >= 0:
        return 60
    elif margin >= -0.05:
        return 40
    else:
        return 20


# ==========================================================
# 4 - BORÇLULUK SKORU
# AĞIRLIK: %15
# ==========================================================

def calculate_debt_score(current):

    short_term = current.get("short_term_financial_debt") or 0
    current_long_term = current.get("current_portion_long_term_debt") or 0
    long_term = current.get("long_term_financial_debt") or 0
    cash = current.get("cash") or 0
    equity = current.get("equity")

    total_debt = (
        float(short_term)
        + float(current_long_term)
        + float(long_term)
    )

    if equity in (None, 0):
        return 50

    net_debt = total_debt - float(cash)
    net_debt_equity = net_debt / float(equity)

    if net_debt_equity <= 0:
        return 100
    elif net_debt_equity <= 0.25:
        return 90
    elif net_debt_equity <= 0.50:
        return 80
    elif net_debt_equity <= 0.75:
        return 70
    elif net_debt_equity <= 1.00:
        return 60
    elif net_debt_equity <= 1.50:
        return 45
    elif net_debt_equity <= 2.00:
        return 30
    else:
        return 15


# ==========================================================
# 5 - ÖZKAYNAK SKORU
# AĞIRLIK: %10
# ==========================================================

def calculate_equity_score(current):

    equity = current.get("equity")
    assets = current.get("total_assets")

    ratio = safe_div(equity, assets)

    if ratio is None:
        return 50

    if ratio >= 0.60:
        return 100
    elif ratio >= 0.50:
        return 90
    elif ratio >= 0.40:
        return 80
    elif ratio >= 0.30:
        return 70
    elif ratio >= 0.20:
        return 55
    elif ratio >= 0.10:
        return 40
    else:
        return 20


# ==========================================================
# 6 - NAKİT AKIŞI SKORU
# AĞIRLIK: %15
# ==========================================================

def calculate_cash_flow_score(current):

    cfo = current.get("operating_cash_flow")

    if cfo is None:
        return 50

    if cfo > 0:
        return 100
    elif cfo == 0:
        return 50
    else:
        return 15


# ==========================================================
# 7 - BÜYÜME SKORU
# AĞIRLIK: %10
# ==========================================================

def calculate_growth_score(current, previous=None):

    if not previous:
        return 50

    revenue = current.get("revenue")
    previous_revenue = previous.get("revenue")

    if revenue is None or previous_revenue in (None, 0):
        return 50

    growth = (
        float(revenue) - float(previous_revenue)
    ) / abs(float(previous_revenue))

    if growth >= 0.30:
        return 100
    elif growth >= 0.20:
        return 90
    elif growth >= 0.10:
        return 80
    elif growth >= 0.05:
        return 70
    elif growth >= 0:
        return 60
    elif growth >= -0.05:
        return 50
    elif growth >= -0.15:
        return 35
    else:
        return 20


# ==========================================================
# SİNYAL
# ==========================================================

def get_signal(score):

    if score >= 80:
        return "GÜÇLÜ"

    if score >= 65:
        return "POZİTİF"

    if score >= 50:
        return "NÖTR"

    if score >= 35:
        return "ZAYIF"

    return "RİSKLİ"


# ==========================================================
# FİNANSAL SKOR HESAPLA
# ==========================================================

def calculate_financial_score(symbol, period_end=None):

    current = get_financial_statement(
        symbol,
        period_end
    )

    if not current:
        return None

    previous = get_previous_statement(
        symbol,
        current["period_end"]
    )

    revenue_score = calculate_revenue_score(
        current,
        previous
    )

    profit_score = calculate_profit_score(
        current
    )

    margin_score = calculate_margin_score(
        current
    )

    debt_score = calculate_debt_score(
        current
    )

    equity_score = calculate_equity_score(
        current
    )

    cash_flow_score = calculate_cash_flow_score(
        current
    )

    growth_score = calculate_growth_score(
        current,
        previous
    )

    total_score = (
        revenue_score * 0.15
        + profit_score * 0.20
        + margin_score * 0.15
        + debt_score * 0.15
        + equity_score * 0.10
        + cash_flow_score * 0.15
        + growth_score * 0.10
    )

    total_score = round(
        clamp(total_score),
        2
    )

    result = {
        "symbol": current["symbol"],
        "period": current["period"],
        "period_end": current["period_end"],
        "revenue_score": round(revenue_score, 2),
        "profit_score": round(profit_score, 2),
        "margin_score": round(margin_score, 2),
        "debt_score": round(debt_score, 2),
        "equity_score": round(equity_score, 2),
        "cash_flow_score": round(cash_flow_score, 2),
        "growth_score": round(growth_score, 2),
        "total_score": total_score,
        "signal": get_signal(total_score),
        "analysis_date": datetime.now().isoformat(),
    }

    return result


# ==========================================================
# FINANCIAL_SCORES TABLOSUNA KAYDET
# ==========================================================

def save_financial_score_result(result):

    if not result:
        return False

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT INTO financial_scores (
            symbol,
            analysis_date,
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
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, fiscal_year, fiscal_period)
        DO UPDATE SET
            analysis_date = excluded.analysis_date,
            revenue_score = excluded.revenue_score,
            profit_score = excluded.profit_score,
            margin_score = excluded.margin_score,
            debt_score = excluded.debt_score,
            equity_score = excluded.equity_score,
            cash_flow_score = excluded.cash_flow_score,
            growth_score = excluded.growth_score,
            total_score = excluded.total_score,
            signal = excluded.signal
        """,
        (
            result["symbol"],
            result["analysis_date"],
            int(str(result["period_end"])[:4]),
            result["period"],
            result["revenue_score"],
            result["profit_score"],
            result["margin_score"],
            result["debt_score"],
            result["equity_score"],
            result["cash_flow_score"],
            result["growth_score"],
            result["total_score"],
            result["signal"],
        ),
    )

    conn.commit()
    conn.close()

    return True


# ==========================================================
# HESAPLA + KAYDET
# ==========================================================

def calculate_and_save_financial_score(
    symbol,
    period_end=None
):

    result = calculate_financial_score(
        symbol,
        period_end
    )

    if not result:
        return None

    save_financial_score_result(result)

    return result